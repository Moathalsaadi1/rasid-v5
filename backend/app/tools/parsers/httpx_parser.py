"""Httpx JSONL output parser."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Parse httpx JSONL into a list of endpoint dicts.

    Each item: {url, scheme, host, port, path, status_code, title, webserver}
    """
    results: list[dict[str, Any]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        url = item.get("url")
        if not url:
            continue

        parsed_url = urlparse(url)
        results.append({
            "url": url,
            "scheme": parsed_url.scheme,
            "host": parsed_url.hostname,
            "port": parsed_url.port,
            "path": parsed_url.path or "/",
            "status_code": item.get("status_code"),
            "title": item.get("title"),
            "webserver": item.get("webserver"),
        })

    return results
