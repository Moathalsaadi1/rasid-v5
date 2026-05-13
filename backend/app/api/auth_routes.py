"""Authentication endpoints: register, login, current user."""
from __future__ import annotations

import secrets

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import get_json_body, require_api_key
from app.db import SessionLocal
from app.models import User, UserRole
from app.security import hash_password, verify_password


bp = Blueprint("auth", __name__, url_prefix="/api")


# Pre-computed hash used to make the "user not found" path do the same
# amount of work as the "user found but wrong password" path. Without
# this an attacker can enumerate valid emails by measuring response
# times (password verification is intentionally slow, so the timing
# difference is observable). The plaintext doesn't matter — we never
# compare against it; we only execute verify_password so that its
# CPU cost is paid either way.
_DUMMY_PASSWORD_HASH = hash_password("rasid-timing-attack-shield-placeholder")


@bp.post("/register")
def register():
    data = get_json_body()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"ok": False, "error": "email and password required"}), 400

    if len(password) < 8:
        return jsonify({"ok": False, "error": "password must be at least 8 characters"}), 400

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).one_or_none():
            return jsonify({"ok": False, "error": "email already exists"}), 400

        is_first = db.query(User).count() == 0
        role = UserRole.ADMIN.value if is_first else UserRole.USER.value

        user = User(
            email=email,
            password_hash=hash_password(password),
            api_key="rasid_" + secrets.token_urlsafe(32),
            role=role,
        )
        db.add(user)
        db.flush()
        audit(db, user_id=user.id, action="user.register",
              resource_type="user", resource_id=str(user.id))
        db.commit()
        db.refresh(user)

        return jsonify({
            "ok": True,
            "user": {
                "id": user.id, "email": user.email,
                "api_key": user.api_key, "role": user.role,
            },
        })
    finally:
        db.close()


@bp.post("/login")
def login():
    data = get_json_body()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"ok": False, "error": "email and password required"}), 400

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).one_or_none()

        # Constant-time-ish handling: always run a password verification,
        # even when the user does not exist, so an attacker can't
        # distinguish "unknown email" from "wrong password" by latency.
        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            audit(db, user_id=None, action="user.login_failed",
                  resource_type="user", resource_id=email, commit=True)
            return jsonify({"ok": False, "error": "invalid credentials"}), 401

        if not verify_password(password, user.password_hash):
            audit(db, user_id=user.id, action="user.login_failed",
                  resource_type="user", resource_id=email, commit=True)
            return jsonify({"ok": False, "error": "invalid credentials"}), 401

        if not user.is_active:
            audit(db, user_id=user.id, action="user.login_blocked",
                  resource_type="user", resource_id=str(user.id), commit=True)
            return jsonify({"ok": False, "error": "account suspended"}), 403

        audit(db, user_id=user.id, action="user.login",
              resource_type="user", resource_id=str(user.id), commit=True)

        return jsonify({
            "ok": True,
            "user": {
                "id": user.id, "email": user.email,
                "api_key": user.api_key, "role": user.role,
            },
        })
    finally:
        db.close()


@bp.get("/me")
@require_api_key
def me():
    return jsonify({"ok": True, "user": g.current_user})
