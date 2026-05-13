"""Masscan output parser.

Masscan with `-oJ -` emits a JSON array (sometimes streaming JSONL),
where each entry has:
    {
      "ip": "1.2.3.4",
      "timestamp": "1234567890",
      "ports": [{"port": 80, "proto": "tcp", "status": "open", ...}]
    }

The output may be wrapped as a JSON array, or one object per line.
We try both forms.
"""
from __future__ import annotations

import json
from typing import Any


def _try_array(raw_text: str) -> list[dict[str, Any]] | None:
    text = raw_text.strip()
    if not text.startswith("["):
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else None
    except (json.JSONDecodeError, ValueError):
        return None


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Returns a list of services: {ip, port, protocol, state}."""
    items: list[dict[str, Any]] = []

    array = _try_array(raw_text)
    if array is not None:
        items = array
    else:
        for line in raw_text.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]"):
                continue
            try:
                items.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                continue

    services: list[dict[str, Any]] = []
    for entry in items:
        ip = entry.get("ip")
        if not ip:
            continue
        ports = entry.get("ports") or []
        for p in ports:
            port = p.get("port")
            proto = p.get("proto") or "tcp"
            status = p.get("status") or "open"
            if port is None:
                continue
            try:
                port_int = int(port)
            except (TypeError, ValueError):
                continue
            services.append({
                "ip": ip,
                "port": port_int,
                "protocol": proto,
                "state": status,
                "name": "unknown",  # masscan does not do service detection
            })

    return services
