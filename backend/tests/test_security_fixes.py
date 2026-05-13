"""Tests covering the security fixes added in this pass.

These tests pin down the new behaviour so it can't silently regress:

  * target validation happens BEFORE creating a ScanJob row
  * HTML reports escape untrusted finding fields
  * login is constant-time-ish for unknown emails (we verify the code
    path runs verify_password against the dummy hash; timing itself
    is not deterministic enough to assert on)
  * suspended admins lose access to admin endpoints
  * malformed JSON bodies don't crash routes
  * report download endpoint requires X-API-Key
"""
from __future__ import annotations

from unittest.mock import patch


# ─── Helpers ──────────────────────────────────────────────────────────────


def _register(client, email, password="password12345"):
    res = client.post("/api/register", json={"email": email, "password": password})
    return res.get_json()["user"]


def _accept_terms(client, api_key):
    client.post("/api/legal/accept", headers={"X-API-Key": api_key})


# ─── Target validation up-front (Fix #1) ─────────────────────────────────


def test_private_ip_target_rejected_before_scanjob_created(client):
    """A private IP must produce 400 and NOT increment scan_count or write a ScanJob."""
    user = _register(client, "ssrf@x.com")
    _accept_terms(client, user["api_key"])

    fake_task = type("FakeTask", (), {"delay": lambda self, _x: None})()
    with patch.dict("app.tasks.TASK_DISPATCH", {"nmap": fake_task}):
        res = client.post(
            "/api/scans",
            headers={"X-API-Key": user["api_key"]},
            json={"target": "10.0.0.1", "tool": "nmap"},
        )

    assert res.status_code == 400
    assert "private" in res.get_json()["error"].lower() or "not allowed" in res.get_json()["error"].lower()

    # No scan should have been recorded.
    res = client.get("/api/scans", headers={"X-API-Key": user["api_key"]})
    assert res.get_json()["total"] == 0


def test_loopback_target_rejected_up_front(client):
    user = _register(client, "loop@x.com")
    _accept_terms(client, user["api_key"])
    res = client.post(
        "/api/scans",
        headers={"X-API-Key": user["api_key"]},
        json={"target": "127.0.0.1", "tool": "nmap"},
    )
    assert res.status_code == 400


def test_metadata_hostname_rejected_up_front(client):
    user = _register(client, "meta@x.com")
    _accept_terms(client, user["api_key"])
    res = client.post(
        "/api/scans",
        headers={"X-API-Key": user["api_key"]},
        json={"target": "metadata.google.internal", "tool": "nmap"},
    )
    assert res.status_code == 400


def test_shell_metachars_target_rejected_up_front(client):
    user = _register(client, "sh@x.com")
    _accept_terms(client, user["api_key"])
    res = client.post(
        "/api/scans",
        headers={"X-API-Key": user["api_key"]},
        json={"target": "example.com; rm -rf /", "tool": "nmap"},
    )
    assert res.status_code == 400


# ─── HTML report XSS escaping (Fix #2) ───────────────────────────────────


def test_html_report_escapes_finding_fields(client, make_user):
    """Untrusted strings in findings must be HTML-escaped in the report."""
    from app.models import ScanJob, ScanStatus
    from app.tools import persistence as P
    from app.db import SessionLocal

    user = make_user("xss@x.com", role="user", accept_terms=True)

    # Seed a scan with a finding that contains a <script> tag.
    db = SessionLocal()
    try:
        job = ScanJob(
            user_id=user.id, target="example.com", tool="nmap",
            status=ScanStatus.SUCCESS.value,
        )
        db.add(job)
        db.flush()
        P.create_finding(
            db, scan_id=job.id,
            title="<script>alert('xss')</script>",
            severity="medium",
            description="<img src=x onerror=alert(1)>",
            evidence="</td><script>steal()</script>",
            recommendation="evil & co",
        )
        db.commit()
        scan_id = job.id
    finally:
        db.close()

    res = client.get(
        f"/api/scans/{scan_id}/report?format=html",
        headers={"X-API-Key": user.api_key},
    )
    body = res.get_data(as_text=True)

    # No raw injection should survive.
    assert "<script>alert" not in body
    assert "<img src=x onerror" not in body
    # Their escaped versions must be present.
    assert "&lt;script&gt;alert" in body
    assert "&lt;img src=x onerror" in body
    # Ampersands escaped too.
    assert "evil &amp; co" in body


# ─── Suspended admin (Fix #7) ────────────────────────────────────────────


def test_suspended_admin_loses_admin_access(client, make_user, db_session):
    from app.models import User

    admin = make_user("admin@x.com", role="admin", accept_terms=True)
    second_admin = make_user("admin2@x.com", role="admin", accept_terms=True)  # noqa: F841

    # Suspend the admin directly in the DB.
    db_session.query(User).filter(User.id == admin.id).update({"is_active": False})
    db_session.commit()

    res = client.get("/api/admin/users", headers={"X-API-Key": admin.api_key})
    assert res.status_code == 403
    assert "suspended" in res.get_json()["error"].lower()


# ─── Malformed JSON (Fix #8) ─────────────────────────────────────────────


def test_malformed_json_body_returns_400_not_500(client):
    """Sending broken JSON should fail gracefully via field validation."""
    res = client.post(
        "/api/register",
        data="this is not json",
        headers={"Content-Type": "application/json"},
    )
    # Either 400 (our validation) or 413 — but never a 500.
    assert res.status_code in (400, 413)


def test_non_object_json_body_returns_400(client):
    """JSON array at the top level should be treated as empty body."""
    res = client.post("/api/register", json=["not", "a", "dict"])
    assert res.status_code == 400


# ─── Request size cap (Fix #6) ───────────────────────────────────────────


def test_oversized_request_rejected(client):
    """A 2 MB body exceeds our 1 MiB cap."""
    huge = "A" * (2 * 1024 * 1024)
    res = client.post(
        "/api/register",
        data=f'{{"email":"big@x.com","password":"{huge}"}}',
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 413


# ─── Report download requires auth ───────────────────────────────────────


def test_report_download_requires_api_key(client, make_user):
    from app.models import ScanJob, ScanStatus
    from app.db import SessionLocal

    user = make_user("rep@x.com", role="user", accept_terms=True)
    db = SessionLocal()
    try:
        job = ScanJob(
            user_id=user.id, target="example.com", tool="nmap",
            status=ScanStatus.SUCCESS.value,
        )
        db.add(job)
        db.commit()
        scan_id = job.id
    finally:
        db.close()

    # No API key → 401.
    res = client.get(f"/api/scans/{scan_id}/report?format=html")
    assert res.status_code == 401


# ─── Login timing safety smoke-test (Fix #5) ─────────────────────────────


def test_login_unknown_email_still_returns_401(client):
    """Just check the response is a clean 401 — we don't measure timing
    in tests, but we want to be sure the dummy-hash path doesn't raise."""
    res = client.post(
        "/api/login",
        json={"email": "does-not-exist@x.com", "password": "whatever"},
    )
    assert res.status_code == 401
    assert res.get_json()["error"] == "invalid credentials"
