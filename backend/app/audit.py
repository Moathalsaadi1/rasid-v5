"""
Audit logging — writes append-only entries to the audit_logs table.

Usage:
    from app.audit import audit
    audit(db, action="scan.create", resource_type="scan", resource_id=str(scan.id))

The function tolerates being called outside a Flask request context (e.g.
from Celery tasks) by gracefully omitting the IP / User-Agent fields.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from app.logging_setup import logger
from app.models import AuditLog


def _request_context() -> tuple[Optional[str], Optional[str]]:
    try:
        from flask import has_request_context, request  # noqa: WPS433
    except ImportError:
        return None, None
    if not has_request_context():
        return None, None

    # X-Forwarded-For is trusted only when explicitly opted in via
    # TRUST_PROXY_HEADERS=true — otherwise any client can spoof their IP
    # in the audit log by sending the header themselves. When trusted,
    # take the *first* address in the list (RFC 7239 convention: the
    # original client). When not trusted, fall back to the socket peer.
    import os
    trust_proxy = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    ip: Optional[str] = None
    if trust_proxy:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            ip = xff.split(",")[0].strip() or None
    if not ip:
        ip = request.remote_addr
    if ip and len(ip) > 64:
        ip = ip[:64]

    ua = request.headers.get("User-Agent")
    if ua and len(ua) > 255:
        ua = ua[:255]
    return ip, ua


def audit(
    db,
    *,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    commit: bool = False,
) -> None:
    """Insert an audit_logs row.

    Pass commit=True if there is no surrounding transaction; otherwise the
    caller is expected to commit later. We keep commits out by default to
    avoid breaking endpoints that compose multiple writes.
    """
    ip, ua = _request_context()
    extra_json = json.dumps(extra) if extra else None

    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip,
        user_agent=ua,
        extra=extra_json,
    )
    db.add(row)
    if commit:
        db.commit()

    logger.info(
        "AUDIT user=%s action=%s resource=%s/%s ip=%s",
        user_id, action, resource_type, resource_id, ip,
    )
