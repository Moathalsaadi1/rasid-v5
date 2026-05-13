"""Amass output parser.

Amass with `-json -` emits JSONL where each entry typically has:
    {
      "name": "sub.example.com",
      "domain": "example.com",
      "addresses": [{"ip": "1.2.3.4", "cidr": "...", "asn": ...}],
      "tag": "...",
      "sources": ["dns", "cert"]
    }
"""
from __future__ import annotations

import json
from typing import Any


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Returns deduplicated subdomains with their resolved IPs."""
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Plain text fallback (older amass / non-json mode).
            host = line
            if host and host not in seen:
                seen.add(host)
                results.append({"host": host, "ips": [], "sources": []})
            continue

        host = item.get("name")
        if not host or host in seen:
            continue
        seen.add(host)

        addresses = item.get("addresses") or []
        ips = [a.get("ip") for a in addresses if a.get("ip")]

        results.append({
            "host": host,
            "ips": ips,
            "sources": item.get("sources") or [],
            "tag": item.get("tag"),
        })

    return results
