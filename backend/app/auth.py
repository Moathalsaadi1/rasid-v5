from functools import wraps
from flask import request, jsonify, g

from app.db import SessionLocal
from app.models import User, UserRole


def get_json_body() -> dict:
    """Read JSON body safely.

    - silent=True so malformed JSON returns None instead of raising
      werkzeug.exceptions.BadRequest (which would leak a noisy default
      HTML error page).
    - force=True keeps the previous behaviour of accepting bodies even
      when Content-Type is missing/wrong (some clients are sloppy).
    - We always return a dict; non-dict top-level JSON (e.g. an array
      or a string) is rejected by returning {}, which downstream code
      already treats as "missing fields → 400".
    """
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        return {}
    return data


def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 200)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"ok": False, "error": "missing api key"}), 401

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).one_or_none()
            if not user:
                return jsonify({"ok": False, "error": "invalid api key"}), 401

            if not user.is_active:
                return jsonify({"ok": False, "error": "account suspended"}), 403

            g.current_user = {
                "id": user.id,
                "email": user.email,
                "api_key": user.api_key,
                "role": user.role,
                "scan_count": user.scan_count,
            }

            return fn(*args, **kwargs)
        finally:
            db.close()

    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 200)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return jsonify({"ok": False, "error": "missing api key"}), 401

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).one_or_none()
            if not user:
                return jsonify({"ok": False, "error": "invalid api key"}), 401

            # A suspended admin must not be able to use admin endpoints.
            # The previous version checked role but not is_active, which let
            # a freshly suspended admin keep operating until their session
            # was cleared.
            if not user.is_active:
                return jsonify({"ok": False, "error": "account suspended"}), 403

            if user.role != UserRole.ADMIN.value:
                return jsonify({"ok": False, "error": "admin access required"}), 403

            g.current_user = {
                "id": user.id,
                "email": user.email,
                "api_key": user.api_key,
                "role": user.role,
            }

            return fn(*args, **kwargs)
        finally:
            db.close()

    return wrapper
