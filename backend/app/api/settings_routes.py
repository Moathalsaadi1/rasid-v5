"""Per-user settings endpoints: change password, rotate API key, delete account."""
from __future__ import annotations

import secrets

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import get_json_body, require_api_key
from app.db import SessionLocal
from app.models import User, UserRole
from app.security import hash_password, verify_password


bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@bp.post("/change-password")
@require_api_key
def change_password():
    data = get_json_body()
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return jsonify({"ok": False, "error": "current and new password required"}), 400

    if len(new_password) < 8:
        return jsonify({"ok": False, "error": "new password must be at least 8 characters"}), 400

    if new_password == current_password:
        return jsonify({"ok": False, "error": "new password must differ from current"}), 400

    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        user = db.query(User).filter(User.id == uid).one_or_none()
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        if not verify_password(current_password, user.password_hash):
            audit(db, user_id=uid, action="user.password_change_failed",
                  resource_type="user", resource_id=str(uid), commit=True)
            return jsonify({"ok": False, "error": "current password is incorrect"}), 401

        user.password_hash = hash_password(new_password)
        audit(db, user_id=uid, action="user.password_change",
              resource_type="user", resource_id=str(uid))
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@bp.post("/rotate-api-key")
@require_api_key
def rotate_api_key():
    """Issue a new API key, invalidating the old one immediately.

    The frontend must store the new key and re-attach it to subsequent
    requests — the response includes the new value once and only once.
    """
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        user = db.query(User).filter(User.id == uid).one_or_none()
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        new_key = "rasid_" + secrets.token_urlsafe(32)
        user.api_key = new_key

        audit(db, user_id=uid, action="user.rotate_api_key",
              resource_type="user", resource_id=str(uid))
        db.commit()

        return jsonify({"ok": True, "api_key": new_key})
    finally:
        db.close()


@bp.delete("/account")
@require_api_key
def delete_account():
    """Self-service account deletion. Confirmation requires sending the
    user's current password in the request body — without it we never delete.
    Cascade on the FKs takes care of scans, findings, etc.
    """
    data = get_json_body()
    password = data.get("password") or ""

    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        user = db.query(User).filter(User.id == uid).one_or_none()
        if not user:
            return jsonify({"ok": False, "error": "user not found"}), 404

        if not verify_password(password, user.password_hash):
            audit(db, user_id=uid, action="user.delete_failed_auth",
                  resource_type="user", resource_id=str(uid), commit=True)
            return jsonify({"ok": False, "error": "password is incorrect"}), 401

        # Prevent the last admin from deleting themselves.
        if user.role == UserRole.ADMIN.value:
            admin_count = (
                db.query(User)
                .filter(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
                .count()
            )
            if admin_count <= 1:
                return jsonify({
                    "ok": False,
                    "error": "cannot delete the last active admin account",
                }), 409

        audit(db, user_id=uid, action="user.delete",
              resource_type="user", resource_id=str(uid), commit=True)

        db.delete(user)
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()
