"""Subfinder output parser.

Subfinder with -oJ emits JSONL where each line is:
    {"host": "sub.example.com", "input": "example.com", "source": "..."}
"""
from __future__ import annotations

import json
from typing import Any


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Returns a list of {host, source} dicts. Duplicates removed."""
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Some subfinder versions emit plain hostnames when not in -oJ mode
            host = line
            if host and host not in seen:
                seen.add(host)
                results.append({"host": host, "source": None})
            continue

        host = item.get("host") or item.get("name")
        if not host or host in seen:
            continue
        seen.add(host)
        results.append({
            "host": host,
            "source": item.get("source"),
        })

    return results
