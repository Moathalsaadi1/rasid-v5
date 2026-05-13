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
