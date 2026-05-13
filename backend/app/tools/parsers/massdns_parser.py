"""Massdns output parser.

Massdns with `-o J` emits NDJSON entries:
    {
      "name": "example.com.",
      "type": "A",
      "class": "IN",
      "status": "NOERROR",
      "data": {"answers": [{"name": "...", "type": "A", "data": "1.2.3.4"}]}
    }
"""
from __future__ import annotations

import json
from typing import Any


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Returns a list of {host, ips, status} entries."""
    results: list[dict[str, Any]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        name = item.get("name", "").rstrip(".")
        if not name:
            continue

        status = item.get("status", "UNKNOWN")
        ips: list[str] = []
        data = item.get("data") or {}
        for ans in data.get("answers", []) or []:
            if ans.get("type") in ("A", "AAAA"):
                addr = ans.get("data")
                if addr:
                    ips.append(addr)

        results.append({"host": name, "ips": ips, "status": status})

    return results
