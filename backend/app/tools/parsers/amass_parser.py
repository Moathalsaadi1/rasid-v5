"""
Parses amass v4 output (plain text relationship format):

    example.com (FQDN) --> a_record --> 1.2.3.4 (IPAddress)
    sub.example.com (FQDN) --> a_record --> 5.6.7.8 (IPAddress)

Extracts unique FQDNs and their resolved IPs.
"""
from __future__ import annotations
import re
from typing import Any

# Matches: <name> (<TYPE>) --> <rel> --> <value> (<TYPE>)
LINE_RE = re.compile(
    r"^(\S+)\s+\((\w+)\)\s+-->\s+(\w+)\s+-->\s+(\S+)\s+\((\w+)\)\s*$"
)


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Returns deduplicated FQDNs with their resolved IPs."""
    hosts: dict[str, dict[str, Any]] = {}

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        m = LINE_RE.match(line)
        if not m:
            continue

        src, src_type, rel, dst, dst_type = m.groups()

        # Track every FQDN we see (as source).
        if src_type == "FQDN" and src not in hosts:
            hosts[src] = {"host": src, "ips": [], "sources": []}

        # When source is FQDN and dest is IP, record the IP.
        if src_type == "FQDN" and dst_type == "IPAddress" and rel in (
            "a_record", "aaaa_record",
        ):
            if src not in hosts:
                hosts[src] = {"host": src, "ips": [], "sources": []}
            if dst not in hosts[src]["ips"]:
                hosts[src]["ips"].append(dst)

    return list(hosts.values())
