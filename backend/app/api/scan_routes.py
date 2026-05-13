"""Scan management endpoints: list, create, get details, cancel/delete."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import get_json_body, require_api_key
from app.db import SessionLocal
from app.legal import has_accepted_terms
from app.models import (
    Asset,
    Finding,
    LegalAcceptance,
    ScanAsset,
    ScanJob,
    ScanService,
    ScanStatus,
    ScanWebEndpoint,
    Service,
    User,
    UserRole,
    WebEndpoint,
)
from app.serializers import job_to_dict, finding_to_dict
from app.tools.registry import all_tool_names, is_known_tool
from app.validation import validate_target


bp = Blueprint("scans", __name__, url_prefix="/api")


GUEST_SCAN_LIMIT = 3


@bp.get("/scans")
@require_api_key
def list_scans():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, int(request.args.get("per_page", 20)))
        status_filter = request.args.get("status")
        tool_filter = request.args.get("tool")
        search = (request.args.get("search") or "").strip()

        q = db.query(ScanJob)
        if not is_admin:
            q = q.filter(ScanJob.user_id == uid)
        if status_filter:
            q = q.filter(ScanJob.status == status_filter.upper())
        if tool_filter:
            q = q.filter(ScanJob.tool == tool_filter.lower())
        if search:
            like = f"%{search}%"
            q = q.filter(ScanJob.target.ilike(like))

        total = q.count()
        jobs = q.order_by(ScanJob.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "ok": True,
            "scans": [job_to_dict(j) for j in jobs],
            "total": total, "page": page, "per_page": per_page,
        })
    finally:
        db.close()


@bp.post("/scans")
@require_api_key
def create_scan():
    from app.tasks import TASK_DISPATCH

    data = get_json_body()
    target = (data.get("target") or "").strip()
    tool = (data.get("tool") or "nmap").strip().lower()

    if not target:
        return jsonify({"ok": False, "error": "target is required"}), 400

    if not is_known_tool(tool):
        return jsonify({
            "ok": False,
            "error": f"tool must be one of: {', '.join(all_tool_names())}",
        }), 400

    # ── SECURITY: validate target BEFORE creating any DB row ──────────────
    # Previously, target validation only ran inside the Celery worker
    # (tasks._run_scan_task). That left a window where unsafe targets
    # (private IPs, metadata endpoints, shell-injection chars) could be
    # persisted to scan_jobs, audit_logs, and increment the user's scan
    # counter before being rejected. We now reject up-front.
    target_check = validate_target(target)
    if not target_check.ok:
        return jsonify({"ok": False, "error": target_check.reason}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == g.current_user["id"]).one()

        # Legal acceptance gate (Phase 5)
        if not has_accepted_terms(db, user.id):
            return jsonify({
                "ok": False,
                "error": "legal_acceptance_required",
                "message": "Please accept the platform terms before running scans.",
            }), 403

        # Guest limit
        if user.role == UserRole.GUEST.value and user.scan_count >= GUEST_SCAN_LIMIT:
            return jsonify({
                "ok": False,
                "error": f"Guest accounts are limited to {GUEST_SCAN_LIMIT} scans. Please register for full access.",
            }), 403

        job = ScanJob(
            user_id=user.id,
            target=target,
            tool=tool,
            status=ScanStatus.PENDING.value,
        )
        db.add(job)
        user.scan_count += 1
        db.flush()
        audit(db, user_id=user.id, action="scan.create",
              resource_type="scan", resource_id=str(job.id),
              extra={"target": target, "tool": tool})
        db.commit()
        db.refresh(job)

        TASK_DISPATCH[tool].delay(job.id)

        return jsonify({
            "ok": True, "scan_id": job.id,
            "status": job.status, "tool": job.tool, "target": job.target,
        }), 201
    finally:
        db.close()


@bp.get("/scans/<int:scan_id>")
@require_api_key
def get_scan(scan_id: int):
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        q = db.query(ScanJob).filter(ScanJob.id == scan_id)
        if not is_admin:
            q = q.filter(ScanJob.user_id == uid)
        job = q.one_or_none()

        if not job:
            return jsonify({"ok": False, "error": "scan not found"}), 404

        findings = (
            db.query(Finding)
            .filter(Finding.scan_id == job.id)
            .order_by(Finding.risk_score.desc())
            .all()
        )

        assets_rows = (
            db.query(ScanAsset, Asset)
            .join(Asset, Asset.id == ScanAsset.asset_id)
            .filter(ScanAsset.scan_id == job.id)
            .all()
        )

        services_rows = (
            db.query(ScanService, Service)
            .join(Service, Service.id == ScanService.service_id)
            .filter(ScanService.scan_id == job.id)
            .all()
        )

        web_rows = (
            db.query(ScanWebEndpoint, WebEndpoint)
            .join(WebEndpoint, WebEndpoint.id == ScanWebEndpoint.web_endpoint_id)
            .filter(ScanWebEndpoint.scan_id == job.id)
            .all()
        )

        scan_dict = job_to_dict(job)
        scan_dict["findings"] = [finding_to_dict(f) for f in findings]
        scan_dict["assets"] = [
            {"id": a.id, "type": a.type, "value": a.value, "role": sa.role}
            for sa, a in assets_rows
        ]
        scan_dict["services"] = [
            {"id": svc.id, "port": svc.port, "protocol": svc.protocol,
             "state": svc.state, "name": svc.name}
            for _, svc in services_rows
        ]
        scan_dict["web_endpoints"] = [
            {"id": ep.id, "url": ep.url, "status_code": ep.status_code,
             "title": ep.title, "webserver": ep.webserver}
            for _, ep in web_rows
        ]

        return jsonify({"ok": True, "scan": scan_dict})
    finally:
        db.close()


@bp.delete("/scans/<int:scan_id>")
@require_api_key
def delete_scan(scan_id: int):
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        q = db.query(ScanJob).filter(ScanJob.id == scan_id)
        if not is_admin:
            q = q.filter(ScanJob.user_id == uid)
        job = q.one_or_none()
        if not job:
            return jsonify({"ok": False, "error": "scan not found"}), 404

        # Don't allow deletion while a scan is mid-flight; ask the user to
        # cancel first. (In a future iteration we can add a real cancel
        # signal that aborts the running container.)
        if job.status == ScanStatus.RUNNING.value:
            return jsonify({"ok": False,
                            "error": "cannot delete a running scan; cancel it first"}), 409

        audit(db, user_id=uid, action="scan.delete",
              resource_type="scan", resource_id=str(job.id))
        db.delete(job)
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@bp.post("/scans/<int:scan_id>/cancel")
@require_api_key
def cancel_scan(scan_id: int):
    """Mark a scan as failed with reason 'cancelled'.

    Note: this does NOT kill the underlying Docker container — that requires
    Celery task revocation plus container.kill, which we leave for a future
    enhancement. For now this is a soft-cancel that lets the user move on.
    """
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        q = db.query(ScanJob).filter(ScanJob.id == scan_id)
        if not is_admin:
            q = q.filter(ScanJob.user_id == uid)
        job = q.one_or_none()
        if not job:
            return jsonify({"ok": False, "error": "scan not found"}), 404

        if job.status not in (ScanStatus.PENDING.value, ScanStatus.RUNNING.value):
            return jsonify({"ok": False,
                            "error": f"cannot cancel scan in status {job.status}"}), 409

        from datetime import datetime, timezone
        job.status = ScanStatus.FAILED.value
        job.error_message = "Cancelled by user"
        job.finished_at = datetime.now(timezone.utc)

        audit(db, user_id=uid, action="scan.cancel",
              resource_type="scan", resource_id=str(job.id))
        db.commit()

        return jsonify({"ok": True, "scan_id": job.id, "status": job.status})
    finally:
        db.close()


@bp.get("/scans/<int:scan_id>/raw")
@require_api_key
def get_scan_raw(scan_id: int):
    """Returns the raw stdout/stderr captured from the tool container."""
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        q = db.query(ScanJob).filter(ScanJob.id == scan_id)
        if not is_admin:
            q = q.filter(ScanJob.user_id == uid)
        job = q.one_or_none()
        if not job:
            return jsonify({"ok": False, "error": "scan not found"}), 404

        return jsonify({
            "ok": True,
            "scan_id": job.id,
            "stdout": job.stdout or "",
            "stderr": job.stderr or "",
            "error_message": job.error_message,
        })
    finally:
        db.close()
