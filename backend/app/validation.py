"""
Target validation utilities for RASID.

Centralizes all checks that determine whether a user-supplied target is
safe to scan. The previous implementation only blocked shell metachars,
which left several SSRF avenues open:

  * loopback addresses (127.0.0.0/8, ::1)
  * link-local / cloud metadata (169.254.0.0/16 — including 169.254.169.254)
  * RFC1918 private ranges (10/8, 172.16/12, 192.168/16)
  * "localhost" and similar hostnames

This module rejects all of the above unless explicitly allowed via the
ALLOW_PRIVATE_TARGETS env var (intended for self-hosted lab use only).
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from urllib.parse import urlparse


# ─── Configuration ─────────────────────────────────────────────────────────

_ALLOW_PRIVATE = os.getenv("ALLOW_PRIVATE_TARGETS", "false").lower() == "true"

# Hostnames that resolve to loopback/private and should be blocked by name
_BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "broadcasthost",
    # AWS / GCP / Azure metadata endpoints (case-insensitive)
    "metadata.google.internal",
    "metadata.azure.com",
}

# Shell injection metachars (kept from the original simple check)
_BAD_CHARS = (";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "\r", "\\")


# ─── Result type ───────────────────────────────────────────────────────────

class ValidationResult:
    __slots__ = ("ok", "reason")

    def __init__(self, ok: bool, reason: str = ""):
        self.ok = ok
        self.reason = reason

    def __bool__(self):
        return self.ok


# ─── Helpers ───────────────────────────────────────────────────────────────

def _strip_url(value: str) -> str:
    """Extract host from full URL, or return the raw value unchanged."""
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname:
            return parsed.hostname
    return value


def _is_private_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _has_bad_chars(value: str) -> bool:
    return any(bad in value for bad in _BAD_CHARS)


def _looks_like_hostname(value: str) -> bool:
    # Hostname pattern (letters, digits, dots, hyphens). Rough but sufficient
    # — we use this only to decide "should we even attempt DNS resolution".
    return bool(re.match(r"^[A-Za-z0-9._-]+$", value)) and len(value) <= 253


def _resolve_hostname(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
        return list({info[4][0] for info in infos})
    except (socket.gaierror, socket.herror):
        return []


# ─── Public API ────────────────────────────────────────────────────────────

def validate_target(target: str) -> ValidationResult:
    """
    Validate a user-supplied scan target.

    Returns ValidationResult(ok=True) when the target is safe to scan, or
    ValidationResult(ok=False, reason=...) with a human-readable reason.

    Truthy/falsy: ValidationResult is bool-castable so existing code can use
    `if not validate_target(t): ...`.
    """
    if not target or not isinstance(target, str):
        return ValidationResult(False, "target is required")

    target = target.strip()

    if len(target) == 0 or len(target) > 255:
        return ValidationResult(False, "target length must be between 1 and 255")

    if _has_bad_chars(target):
        return ValidationResult(False, "target contains forbidden characters")

    host = _strip_url(target).lower().strip("/")

    # Blocked by name regardless of resolution
    if host in _BLOCKED_HOSTNAMES:
        if not _ALLOW_PRIVATE:
            return ValidationResult(False, f"hostname '{host}' is not allowed")

    # Try to parse as a literal IP first
    try:
        ip = ipaddress.ip_address(host)
        if _is_private_ip(ip) and not _ALLOW_PRIVATE:
            return ValidationResult(False, f"private/reserved IP '{host}' is not allowed")
        return ValidationResult(True)
    except ValueError:
        pass  # Not an IP literal; treat as hostname

    if not _looks_like_hostname(host):
        return ValidationResult(False, "target is not a valid hostname or IP")

    # Resolve and check every returned address. If any resolves to a private
    # range, block it (DNS rebinding-lite protection — best-effort, not
    # bulletproof since the resolver may give different results to the
    # scanner; deeper protection would require pinning the resolved IP).
    if not _ALLOW_PRIVATE:
        addresses = _resolve_hostname(host)
        for addr in addresses:
            try:
                ip = ipaddress.ip_address(addr)
                if _is_private_ip(ip):
                    return ValidationResult(
                        False,
                        f"hostname '{host}' resolves to a private address and is not allowed",
                    )
            except ValueError:
                continue

    return ValidationResult(True)


def is_safe_target(target: str) -> bool:
    """Backwards-compatible boolean wrapper."""
    return bool(validate_target(target))
