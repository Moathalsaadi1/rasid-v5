"""Tests for scan creation flow + the legal gate + permissions."""
from __future__ import annotations

from unittest.mock import patch


def _register(client, email, password="password12345"):
    """Register a user and return (api_key, user_dict)."""
    res = client.post("/api/register", json={"email": email, "password": password})
    user = res.get_json()["user"]
    return user["api_key"], user


def _accept_terms(client, api_key):
    res = client.post("/api/legal/accept", headers={"X-API-Key": api_key})
    assert res.status_code == 200


# ─── Legal gate ──────────────────────────────────────────────────────────

def test_scan_blocked_before_legal_acceptance(client):
    api_key, _ = _register(client, "noterms@x.com")
    # Patch the Celery dispatch so we don't accidentally try to run a task.
    with patch.dict("app.tasks.TASK_DISPATCH"):
        res = client.post(
            "/api/scans",
            headers={"X-API-Key": api_key},
            json={"target": "scanme.nmap.org", "tool": "nmap"},
        )
    assert res.status_code == 403
    body = res.get_json()
    assert body["error"] == "legal_acceptance_required"


def test_scan_allowed_after_legal_acceptance(client):
    api_key, _ = _register(client, "withterms@x.com")
    _accept_terms(client, api_key)

    # Mock the Celery task so we don't actually try to talk to Docker.
    fake_task = type("FakeTask", (), {"delay": lambda self, _x: None})()
    with patch.dict("app.tasks.TASK_DISPATCH", {"nmap": fake_task}):
        res = client.post(
            "/api/scans",
            headers={"X-API-Key": api_key},
            json={"target": "scanme.nmap.org", "tool": "nmap"},
        )
    assert res.status_code == 201
    body = res.get_json()
    assert body["scan_id"]
    assert body["tool"] == "nmap"
    assert body["target"] == "scanme.nmap.org"


# ─── Tool validation ─────────────────────────────────────────────────────

def test_unknown_tool_rejected(client):
    api_key, _ = _register(client, "unknown@x.com")
    _accept_terms(client, api_key)
    res = client.post(
        "/api/scans",
        headers={"X-API-Key": api_key},
        json={"target": "example.com", "tool": "metasploit"},
    )
    assert res.status_code == 400
    assert "tool must be one of" in res.get_json()["error"]


def test_missing_target_rejected(client):
    api_key, _ = _register(client, "notarget@x.com")
    _accept_terms(client, api_key)
    res = client.post(
        "/api/scans",
        headers={"X-API-Key": api_key},
        json={"tool": "nmap"},
    )
    assert res.status_code == 400


# ─── All 7 tools recognized ──────────────────────────────────────────────

def test_all_seven_tools_recognised(client):
    api_key, _ = _register(client, "all@x.com")
    _accept_terms(client, api_key)

    fake_task = type("FakeTask", (), {"delay": lambda self, _x: None})()
    full_dispatch = {
        "nmap": fake_task, "httpx": fake_task, "nuclei": fake_task,
        "subfinder": fake_task, "amass": fake_task,
        "masscan": fake_task, "massdns": fake_task,
    }
    with patch.dict("app.tasks.TASK_DISPATCH", full_dispatch, clear=False):
        for tool in ["nmap", "httpx", "nuclei", "subfinder", "amass", "masscan", "massdns"]:
            res = client.post(
                "/api/scans",
                headers={"X-API-Key": api_key},
                json={"target": "example.com", "tool": tool},
            )
            assert res.status_code == 201, f"{tool} failed: {res.get_json()}"


# ─── Permission boundaries ───────────────────────────────────────────────

def test_user_cannot_see_others_scans(client):
    a_key, _ = _register(client, "alice@x.com")
    _accept_terms(client, a_key)

    b_key, _ = _register(client, "bob@x.com")
    _accept_terms(client, b_key)

    fake_task = type("FakeTask", (), {"delay": lambda self, _x: None})()
    with patch.dict("app.tasks.TASK_DISPATCH", {"nmap": fake_task}):
        res = client.post(
            "/api/scans",
            headers={"X-API-Key": a_key},
            json={"target": "example.com", "tool": "nmap"},
        )
    alice_scan_id = res.get_json()["scan_id"]

    # Bob lists his scans — Alice's should NOT appear.
    res = client.get("/api/scans", headers={"X-API-Key": b_key})
    body = res.get_json()
    assert all(s["id"] != alice_scan_id for s in body["scans"])

    # Bob tries to read Alice's scan directly — gets 404.
    res = client.get(f"/api/scans/{alice_scan_id}", headers={"X-API-Key": b_key})
    assert res.status_code == 404


def test_admin_can_see_all_scans(client):
    admin_key, _ = _register(client, "admin@x.com")
    user_key, _ = _register(client, "user@x.com")
    _accept_terms(client, admin_key)
    _accept_terms(client, user_key)

    fake_task = type("FakeTask", (), {"delay": lambda self, _x: None})()
    with patch.dict("app.tasks.TASK_DISPATCH", {"nmap": fake_task}):
        client.post(
            "/api/scans",
            headers={"X-API-Key": user_key},
            json={"target": "example.com", "tool": "nmap"},
        )

    res = client.get("/api/scans", headers={"X-API-Key": admin_key})
    assert res.get_json()["total"] >= 1


# ─── Custom args dispatch ───────────────────────────────────────────────

def test_custom_args_must_be_a_list(client):
    api_key, _ = _register(client, "cmd@x.com")
    res = client.post(
        "/api/tools/commands",
        headers={"X-API-Key": api_key},
        json={"tool_name": "nmap", "args": "not a list"},
    )
    assert res.status_code == 400


def test_custom_args_whitelist_enforced_via_api(client):
    api_key, _ = _register(client, "wl@x.com")
    res = client.post(
        "/api/tools/commands",
        headers={"X-API-Key": api_key},
        json={"tool_name": "nmap", "args": ["-iL", "/etc/passwd"]},
    )
    assert res.status_code == 400
    assert "not allowed" in res.get_json()["error"]


def test_custom_args_create_and_list(client):
    api_key, _ = _register(client, "ok@x.com")
    res = client.post(
        "/api/tools/commands",
        headers={"X-API-Key": api_key},
        json={"tool_name": "nmap", "args": ["-T4", "-F", "-oX", "-"]},
    )
    assert res.status_code == 200

    res = client.get("/api/tools/commands", headers={"X-API-Key": api_key})
    body = res.get_json()
    assert len(body["commands"]) == 1
    assert body["commands"][0]["tool_name"] == "nmap"
    assert body["commands"][0]["args"] == ["-T4", "-F", "-oX", "-"]


def test_tools_endpoint_lists_seven(client):
    api_key, _ = _register(client, "tl@x.com")
    res = client.get("/api/tools", headers={"X-API-Key": api_key})
    assert res.status_code == 200
    names = {t["name"] for t in res.get_json()["tools"]}
    assert names == {"nmap", "httpx", "nuclei", "subfinder", "amass", "masscan", "massdns"}
