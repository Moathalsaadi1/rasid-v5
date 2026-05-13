"""Admin-only endpoints: user management, stats, audit log viewer."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import get_json_body, require_admin
from app.db import SessionLocal
from app.models import (
    Asset,
    AuditLog,
    Finding,
    ScanJob,
    User,
    UserRole,
)
from app.serializers import audit_to_dict


bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/users")
@require_admin
def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        return jsonify({
            "ok": True,
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                    "scan_count": u.scan_count,
                    "created_at": u.created_at,
                }
                for u in users
            ],
        })
    finally:
        db.close()


@bp.put("/users/<int:user_id>")
@require_admin
def update_user(user_id: int):
    data = get_json_body()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).one_or_none()
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        changes: dict[str, object] = {}

        if "role" in data and data["role"] in [r.value for r in UserRole]:
            # Prevent demoting the last remaining admin — would lock the
            # platform out of itself.
            if user.role == UserRole.ADMIN.value and data["role"] != UserRole.ADMIN.value:
                admin_count = (
                    db.query(User)
                    .filter(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
                    .count()
                )
                if admin_count <= 1:
                    return jsonify({
                        "ok": False,
                        "error": "cannot demote the last active admin",
                    }), 409
            changes["role"] = (user.role, data["role"])
            user.role = data["role"]

        if "is_active" in data:
            new_active = bool(data["is_active"])
            # Same protection for suspending the last admin.
            if user.role == UserRole.ADMIN.value and not new_active:
                admin_count = (
                    db.query(User)
                    .filter(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
                    .count()
                )
                if admin_count <= 1:
                    return jsonify({
                        "ok": False,
                        "error": "cannot suspend the last active admin",
                    }), 409
            changes["is_active"] = (user.is_active, new_active)
            user.is_active = new_active

        if changes:
            audit(db, user_id=g.current_user["id"], action="admin.update_user",
                  resource_type="user", resource_id=str(user.id),
                  extra={"changes": {k: {"from": v[0], "to": v[1]} for k, v in changes.items()}})

        db.commit()

        return jsonify({
            "ok": True,
            "user": {
                "id": user.id, "role": user.role, "is_active": user.is_active,
            },
        })
    finally:
        db.close()


@bp.get("/stats")
@require_admin
def stats():
    db = SessionLocal()
    try:
        from app.models import ScanStatus
        return jsonify({
            "ok": True,
            "stats": {
                "total_users": db.query(User).count(),
                "total_scans": db.query(ScanJob).count(),
                "total_findings": db.query(Finding).count(),
                "total_assets": db.query(Asset).count(),
                "running_scans": db.query(ScanJob).filter(
                    ScanJob.status == ScanStatus.RUNNING.value).count(),
            },
        })
    finally:
        db.close()


@bp.get("/audit-logs")
@require_admin
def list_audit_logs():
    """Append-only viewer of audit_logs. Filterable by user, action, date."""
    db = SessionLocal()
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, int(request.args.get("per_page", 50)))
        user_id_filter = request.args.get("user_id")
        action_filter = request.args.get("action")

        q = db.query(AuditLog)
        if user_id_filter:
            try:
                q = q.filter(AuditLog.user_id == int(user_id_filter))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "user_id must be integer"}), 400
        if action_filter:
            q = q.filter(AuditLog.action == action_filter)

        total = q.count()
        rows = (
            q.order_by(AuditLog.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "ok": True,
            "logs": [audit_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        })
    finally:
        db.close()
