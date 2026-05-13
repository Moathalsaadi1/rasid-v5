"""Legal acceptance endpoints (Phase 5, NFR-9).

The first scan a user creates is blocked by scan_routes until they have
accepted the platform's terms; these endpoints let them read the terms
and record their acceptance.
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import require_api_key
from app.db import SessionLocal
from app.legal import CURRENT_TERMS_VERSION, TERMS_TEXT, has_accepted_terms
from app.models import LegalAcceptance


bp = Blueprint("legal", __name__, url_prefix="/api")


@bp.get("/legal/terms")
@require_api_key
def get_terms():
    """Returns the current terms text and version, plus the caller's status."""
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        return jsonify({
            "ok": True,
            "version": CURRENT_TERMS_VERSION,
            "text": TERMS_TEXT,
            "accepted": has_accepted_terms(db, uid),
        })
    finally:
        db.close()


@bp.post("/legal/accept")
@require_api_key
def accept_terms():
    """Record acceptance of the current terms version.

    If the user has previously accepted an older version, we upsert: the
    row is unique per user, so we update terms_version + accepted_at.
    """
    import os
    db = SessionLocal()
    try:
        uid = g.current_user["id"]

        # Mirror the audit module's IP-trust policy: only honour
        # X-Forwarded-For when explicitly configured, otherwise rely on
        # the socket peer address (which the client can't spoof).
        trust_proxy = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
        ip = None
        if trust_proxy:
            xff = request.headers.get("X-Forwarded-For")
            if xff:
                ip = xff.split(",")[0].strip() or None
        if not ip:
            ip = request.remote_addr or ""
        ip = ip[:64]

        existing = (
            db.query(LegalAcceptance)
            .filter(LegalAcceptance.user_id == uid)
            .one_or_none()
        )
        if existing:
            existing.terms_version = CURRENT_TERMS_VERSION
            existing.ip_address = ip
            from sqlalchemy import func
            existing.accepted_at = func.now()
            row = existing
        else:
            row = LegalAcceptance(
                user_id=uid,
                terms_version=CURRENT_TERMS_VERSION,
                ip_address=ip,
            )
            db.add(row)

        audit(db, user_id=uid, action="legal.accept",
              resource_type="legal_acceptance", resource_id=str(uid),
              extra={"version": CURRENT_TERMS_VERSION})
        db.commit()

        return jsonify({"ok": True, "version": CURRENT_TERMS_VERSION})
    finally:
        db.close()
