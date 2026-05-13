"""Dashboard summary endpoint."""
from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.auth import require_api_key
from app.db import SessionLocal
from app.models import Asset, Finding, ScanAsset, ScanJob, UserRole
from app.serializers import job_to_dict


bp = Blueprint("dashboard", __name__, url_prefix="/api")


@bp.get("/dashboard")
@require_api_key
def dashboard():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        is_admin = g.current_user["role"] == UserRole.ADMIN.value

        if is_admin:
            scans = db.query(ScanJob).order_by(ScanJob.created_at.desc()).all()
        else:
            scans = (
                db.query(ScanJob)
                .filter(ScanJob.user_id == uid)
                .order_by(ScanJob.created_at.desc())
                .all()
            )

        scan_ids = [s.id for s in scans]

        if scan_ids:
            findings = db.query(Finding).filter(Finding.scan_id.in_(scan_ids)).all()
            assets_rows = (
                db.query(ScanAsset, Asset)
                .join(Asset, Asset.id == ScanAsset.asset_id)
                .filter(ScanAsset.scan_id.in_(scan_ids))
                .all()
            )
        else:
            findings = []
            assets_rows = []

        severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            level = (f.priority or "").lower()
            if level in severity:
                severity[level] += 1

        status_counts = {"PENDING": 0, "RUNNING": 0, "SUCCESS": 0, "FAILED": 0}
        for s in scans:
            if s.status in status_counts:
                status_counts[s.status] += 1

        asset_map: dict[int, dict] = {}
        for sa, asset in assets_rows:
            if asset.id not in asset_map:
                asset_map[asset.id] = {
                    "asset_id": asset.id,
                    "value": asset.value,
                    "type": asset.type,
                    "highest_risk_score": 0,
                    "findings_count": 0,
                    "roles": set(),
                }
            asset_map[asset.id]["roles"].add(sa.role)

        for f in findings:
            if f.asset_id and f.asset_id in asset_map:
                asset_map[f.asset_id]["findings_count"] += 1
                asset_map[f.asset_id]["highest_risk_score"] = max(
                    asset_map[f.asset_id]["highest_risk_score"], f.risk_score or 0
                )

        top_assets = sorted(asset_map.values(), key=lambda x: x["highest_risk_score"], reverse=True)[:5]
        for a in top_assets:
            a["roles"] = list(a["roles"])

        tool_counts: dict[str, int] = {}
        for s in scans:
            tool_counts[s.tool] = tool_counts.get(s.tool, 0) + 1

        return jsonify({
            "ok": True,
            "dashboard": {
                "total_scans": len(scans),
                "total_findings": len(findings),
                "severity": severity,
                "status_counts": status_counts,
                "tool_counts": tool_counts,
                "top_assets": top_assets,
                "recent_scans": [job_to_dict(s) for s in scans[:5]],
            },
        })
    finally:
        db.close()
