"""Findings and Assets listing endpoints."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_api_key
from app.db import SessionLocal
from app.models import Asset, Finding, ScanAsset, ScanJob, UserRole
from app.serializers import finding_to_dict


bp = Blueprint("data", __name__, url_prefix="/api")


@bp.get("/findings")
@require_api_key
def list_findings():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, int(request.args.get("per_page", 25)))
        severity_filter = request.args.get("severity")
        priority_filter = request.args.get("priority")

        if is_admin:
            scan_ids = [s.id for s in db.query(ScanJob.id).all()]
        else:
            scan_ids = [s.id for s in db.query(ScanJob.id).filter(ScanJob.user_id == uid).all()]

        if not scan_ids:
            return jsonify({
                "ok": True, "findings": [], "total": 0,
                "page": page, "per_page": per_page,
            })

        q = db.query(Finding).filter(Finding.scan_id.in_(scan_ids))
        if severity_filter:
            q = q.filter(Finding.severity == severity_filter.lower())
        if priority_filter:
            q = q.filter(Finding.priority == priority_filter.lower())

        total = q.count()
        findings = (
            q.order_by(Finding.risk_score.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "ok": True,
            "findings": [finding_to_dict(f) for f in findings],
            "total": total, "page": page, "per_page": per_page,
        })
    finally:
        db.close()


@bp.get("/assets")
@require_api_key
def list_assets():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, int(request.args.get("per_page", 25)))

        if is_admin:
            scan_ids = [s.id for s in db.query(ScanJob.id).all()]
        else:
            scan_ids = [s.id for s in db.query(ScanJob.id).filter(ScanJob.user_id == uid).all()]

        if not scan_ids:
            return jsonify({
                "ok": True, "assets": [], "total": 0,
                "page": page, "per_page": per_page,
            })

        asset_ids_q = (
            db.query(ScanAsset.asset_id)
            .filter(ScanAsset.scan_id.in_(scan_ids))
            .distinct()
        )
        asset_ids = [r[0] for r in asset_ids_q.all()]

        total = len(asset_ids)
        paged_ids = asset_ids[(page - 1) * per_page: page * per_page]

        assets = db.query(Asset).filter(Asset.id.in_(paged_ids)).all()

        result = []
        for a in assets:
            findings = (
                db.query(Finding)
                .filter(Finding.asset_id == a.id, Finding.scan_id.in_(scan_ids))
                .all()
            )
            result.append({
                "id": a.id, "type": a.type, "value": a.value,
                "findings_count": len(findings),
                "highest_risk_score": max((f.risk_score for f in findings), default=0),
                "created_at": a.created_at,
            })

        result.sort(key=lambda x: x["highest_risk_score"], reverse=True)

        return jsonify({
            "ok": True, "assets": result, "total": total,
            "page": page, "per_page": per_page,
        })
    finally:
        db.close()


# ─── Aggregated Results ────────────────────────────────────────────────────

@bp.get("/aggregate/<path:target>")
@require_api_key
def get_aggregated(target: str):
    import json
    from app.models import AggregatedResult

    db = SessionLocal()
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, int(request.args.get("per_page", 50)))
        category = request.args.get("category", None)

        base_q = (
            db.query(AggregatedResult)
            .filter_by(target=target)
        )

        # Summary — always full count per category
        all_rows = base_q.all()
        summary: dict[str, int] = {}
        for row in all_rows:
            summary[row.category] = summary.get(row.category, 0) + 1

        # Paginated rows for selected category
        if category:
            filtered = base_q.filter_by(category=category)
        else:
            filtered = base_q

        total = filtered.count()
        rows  = (
            filtered
            .order_by(AggregatedResult.confidence.desc(),
                      AggregatedResult.value)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        grouped: dict[str, list] = {
            "subdomain": [], "port": [],
            "http_endpoint": [], "vulnerability": [],
        }
        for row in rows:
            sources = json.loads(row.sources or "[]")
            meta    = json.loads(row.meta or "{}")
            entry   = {
                "value":      row.value,
                "sources":    sources,
                "confidence": row.confidence,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen":  row.last_seen.isoformat()  if row.last_seen  else None,
                **meta,
            }
            if row.category in grouped:
                grouped[row.category].append(entry)

        return jsonify({
            "ok":      True,
            "target":  target,
            "summary": summary,
            "results": grouped,
            "pagination": {
                "page":       page,
                "per_page":   per_page,
                "total":      total,
                "total_pages": (total + per_page - 1) // per_page,
                "category":   category,
            },
        })
    finally:
        db.close()


# ─── Vulnerability Intelligence ────────────────────────────────────────────

@bp.get("/vuln-intel/<string:cve_id>")
@require_api_key
def get_vuln_intel_endpoint(cve_id: str):
    """Returns educational CVE data from NVD (cached 24h)."""
    from app.vuln_intel import get_vuln_intel

    db = SessionLocal()
    try:
        data = get_vuln_intel(db, cve_id)
        if not data:
            return jsonify({"ok": False, "error": f"No data found for {cve_id}"}), 404
        return jsonify({"ok": True, "intel": data})
    finally:
        db.close()
