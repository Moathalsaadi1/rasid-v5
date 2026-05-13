"""Tests for the auth endpoints: register, login, me."""
from __future__ import annotations


def test_first_registered_user_becomes_admin(client):
    res = client.post("/api/register", json={
        "email": "first@example.com", "password": "password12345",
    })
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert body["user"]["role"] == "admin"
    assert body["user"]["api_key"].startswith("rasid_")


def test_second_user_is_regular(client):
    client.post("/api/register", json={"email": "a@x.com", "password": "password12345"})
    res = client.post("/api/register", json={"email": "b@x.com", "password": "password12345"})
    assert res.get_json()["user"]["role"] == "user"


def test_password_min_length_enforced(client):
    res = client.post("/api/register", json={"email": "x@x.com", "password": "short"})
    assert res.status_code == 400
    assert "8 characters" in res.get_json()["error"]


def test_duplicate_email_rejected(client):
    client.post("/api/register", json={"email": "dup@x.com", "password": "password12345"})
    res = client.post("/api/register", json={"email": "dup@x.com", "password": "password12345"})
    assert res.status_code == 400
    assert "exists" in res.get_json()["error"]


def test_missing_credentials_rejected(client):
    res = client.post("/api/register", json={"email": "noPw@x.com"})
    assert res.status_code == 400


def test_login_with_correct_credentials(client):
    client.post("/api/register", json={"email": "login@x.com", "password": "password12345"})
    res = client.post("/api/login", json={"email": "login@x.com", "password": "password12345"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert body["user"]["api_key"]


def test_login_with_wrong_password_rejected(client):
    client.post("/api/register", json={"email": "user@x.com", "password": "password12345"})
    res = client.post("/api/login", json={"email": "user@x.com", "password": "wrong_password"})
    assert res.status_code == 401


def test_login_with_unknown_email_rejected(client):
    res = client.post("/api/login", json={"email": "ghost@x.com", "password": "password12345"})
    assert res.status_code == 401


def test_me_endpoint_requires_api_key(client):
    res = client.get("/api/me")
    assert res.status_code == 401


def test_me_endpoint_returns_user_with_valid_key(client):
    reg = client.post("/api/register", json={
        "email": "me@x.com", "password": "password12345",
    }).get_json()
    api_key = reg["user"]["api_key"]

    res = client.get("/api/me", headers={"X-API-Key": api_key})
    assert res.status_code == 200
    assert res.get_json()["user"]["email"] == "me@x.com"


def test_invalid_api_key_rejected(client):
    res = client.get("/api/me", headers={"X-API-Key": "invalid_key_xxx"})
    assert res.status_code == 401
