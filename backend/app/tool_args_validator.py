"""
Validation for user-supplied custom command arguments.

Security model: custom args are NEVER passed unmodified to the shell —
they are passed to docker-py as an argv list. But they still need to be
constrained so that a user cannot, say, ask nmap to scan its own host
via -iL or supply a -e (script engine) flag whose effect we did not
budget for.

We enforce a whitelist of *flags* per tool (defined in app.tools.registry).
Values (the strings that follow a flag) are allowed but checked for shell
metachars regardless.
"""
from __future__ import annotations

import re
from typing import Sequence

from app.tools.registry import ToolSpec, get_tool


_VALUE_BAD_CHARS_RE = re.compile(r"[;&|`$<>\\\n\r]")


class ArgsValidationError(ValueError):
    pass


def _is_flag(token: str) -> bool:
    # Plain "-" means stdout/stdin (used by nmap -oX -, amass -json -, etc).
    # Treat it as a value, not a flag, so it bypasses the whitelist check.
    return token.startswith("-") and token != "-"


def _is_placeholder(token: str) -> bool:
    return token == "{TARGET}"


def validate_args(tool_name: str, args: Sequence[str]) -> list[str]:
    """Validate a list of custom args for a given tool.

    Rules:
      * No empty list (must contain at least one token).
      * No more than 32 tokens (sanity cap).
      * Each token: max 200 chars, no shell metachars.
      * Every flag (starts with '-') must appear in spec.allowed_flags.
      * The {TARGET} placeholder is always allowed.
      * Value tokens (non-flag, non-placeholder) are otherwise free-form
        but limited to safe characters.

    Returns the cleaned list (stripped tokens) on success, or raises
    ArgsValidationError on any rule violation.
    """
    spec: ToolSpec | None = get_tool(tool_name)
    if not spec:
        raise ArgsValidationError(f"Unknown tool: {tool_name}")

    if not args:
        raise ArgsValidationError("Args list must not be empty")

    if len(args) > 32:
        raise ArgsValidationError("Too many arguments (max 32)")

    cleaned: list[str] = []
    for raw in args:
        if not isinstance(raw, str):
            raise ArgsValidationError("All arguments must be strings")

        token = raw.strip()
        if not token:
            raise ArgsValidationError("Empty argument is not allowed")

        if len(token) > 200:
            raise ArgsValidationError(f"Argument too long: {token[:30]}…")

        if _VALUE_BAD_CHARS_RE.search(token):
            raise ArgsValidationError(f"Argument contains forbidden characters: {token!r}")

        if _is_flag(token):
            if token not in spec.allowed_flags:
                raise ArgsValidationError(
                    f"Flag {token!r} is not allowed for tool {tool_name}. "
                    f"Allowed flags: {sorted(spec.allowed_flags)}"
                )

        cleaned.append(token)

    return cleaned
