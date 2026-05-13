"""Tests for app.tool_args_validator — the custom-args whitelist enforcer."""
from __future__ import annotations

import pytest

from app.tool_args_validator import ArgsValidationError, validate_args


# ─── Valid usage ──────────────────────────────────────────────────────────

def test_default_nmap_args_pass():
    cleaned = validate_args("nmap", ["-T3", "-F", "-oX", "-"])
    assert cleaned == ["-T3", "-F", "-oX", "-"]


def test_target_placeholder_allowed():
    cleaned = validate_args("httpx", ["-u", "{TARGET}", "-json", "-silent"])
    assert "{TARGET}" in cleaned


def test_value_after_flag_allowed():
    # Plain values (not starting with `-`) are not subject to the flag
    # whitelist — they're just argument values.
    cleaned = validate_args("nmap", ["-p", "22,80,443"])
    assert cleaned == ["-p", "22,80,443"]


# ─── Invalid usage ────────────────────────────────────────────────────────

def test_unknown_tool_rejected():
    with pytest.raises(ArgsValidationError, match="Unknown tool"):
        validate_args("netcat", ["-l", "1234"])


def test_empty_args_rejected():
    with pytest.raises(ArgsValidationError, match="empty"):
        validate_args("nmap", [])


def test_too_many_args_rejected():
    with pytest.raises(ArgsValidationError, match="Too many"):
        validate_args("nmap", ["-T3"] * 50)


def test_disallowed_flag_rejected():
    # -iL is a real nmap flag, but not in our whitelist — it could be used
    # to read arbitrary files inside the container.
    with pytest.raises(ArgsValidationError, match="not allowed"):
        validate_args("nmap", ["-iL", "/etc/passwd"])


def test_shell_metachar_in_value_rejected():
    with pytest.raises(ArgsValidationError, match="forbidden"):
        validate_args("nmap", ["-T3", "; rm -rf /"])


def test_shell_metachar_pipe_rejected():
    with pytest.raises(ArgsValidationError, match="forbidden"):
        validate_args("nmap", ["-T3", "| curl evil"])


def test_overlong_arg_rejected():
    with pytest.raises(ArgsValidationError, match="too long"):
        validate_args("nmap", ["-T3", "a" * 250])


def test_non_string_rejected():
    with pytest.raises(ArgsValidationError):
        validate_args("nmap", [123])  # type: ignore[list-item]


# ─── Per-tool whitelists are independent ────────────────────────────────

def test_nmap_flag_rejected_for_httpx():
    # -T3 is valid for nmap, not for httpx.
    with pytest.raises(ArgsValidationError, match="not allowed"):
        validate_args("httpx", ["-T3", "{TARGET}"])
