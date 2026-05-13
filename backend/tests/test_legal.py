"""Tests for the legal-acceptance endpoints."""
from __future__ import annotations


def _register(client, email):
    res = client.post("/api/register", json={"email": email, "password": "password12345"})
    return res.get_json()["user"]["api_key"]


def test_terms_endpoint_returns_text(client):
    api_key = _register(client, "t@x.com")
    res = client.get("/api/legal/terms", headers={"X-API-Key": api_key})
    assert res.status_code == 200
    body = res.get_json()
    assert body["version"]
    assert "RASID" in body["text"]
    assert body["accepted"] is False


def test_accept_records_acceptance(client):
    api_key = _register(client, "a@x.com")

    # Before
    assert client.get("/api/legal/terms", headers={"X-API-Key": api_key}).get_json()["accepted"] is False

    # Accept
    res = client.post("/api/legal/accept", headers={"X-API-Key": api_key})
    assert res.status_code == 200

    # After
    assert client.get("/api/legal/terms", headers={"X-API-Key": api_key}).get_json()["accepted"] is True


def test_accept_is_idempotent(client):
    api_key = _register(client, "idem@x.com")
    client.post("/api/legal/accept", headers={"X-API-Key": api_key})
    res = client.post("/api/legal/accept", headers={"X-API-Key": api_key})
    assert res.status_code == 200  # second call should still succeed (upsert)
