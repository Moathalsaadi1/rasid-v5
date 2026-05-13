"""Notifications endpoints (Phase 4)."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.auth import require_api_key
from app.db import SessionLocal
from app.models import Notification
from app.serializers import notification_to_dict


bp = Blueprint("notifications", __name__, url_prefix="/api")


@bp.get("/notifications")
@require_api_key
def list_notifications():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        unread_only = request.args.get("unread") == "1"

        q = db.query(Notification).filter(Notification.user_id == uid)
        if unread_only:
            q = q.filter(Notification.is_read.is_(False))

        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, int(request.args.get("per_page", 20)))

        total = q.count()
        unread_count = (
            db.query(Notification)
            .filter(Notification.user_id == uid, Notification.is_read.is_(False))
            .count()
        )

        rows = (
            q.order_by(Notification.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return jsonify({
            "ok": True,
            "notifications": [notification_to_dict(n) for n in rows],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "per_page": per_page,
        })
    finally:
        db.close()


@bp.put("/notifications/<int:nid>/read")
@require_api_key
def mark_read(nid: int):
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        n = (
            db.query(Notification)
            .filter(Notification.id == nid, Notification.user_id == uid)
            .one_or_none()
        )
        if not n:
            return jsonify({"ok": False, "error": "notification not found"}), 404

        n.is_read = True
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@bp.put("/notifications/read-all")
@require_api_key
def mark_all_read():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        (
            db.query(Notification)
            .filter(Notification.user_id == uid, Notification.is_read.is_(False))
            .update({"is_read": True}, synchronize_session=False)
        )
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
