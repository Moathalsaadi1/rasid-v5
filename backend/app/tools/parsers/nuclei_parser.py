"""Nuclei JSONL output parser."""
from __future__ import annotations

import json
from typing import Any


_SEVERITY_MAP = {
    "info": "info",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}


def normalize_severity(value: str | None) -> str:
    if not value:
        return "info"
    return _SEVERITY_MAP.get(value.lower().strip(), "info")


def parse(raw_text: str) -> list[dict[str, Any]]:
    """Parse nuclei JSONL into structured findings.

    Each item:
      {name, severity, matched_at, template_id, matcher_name,
       extracted_results, evidence}
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

        info = item.get("info", {}) or {}
        severity = normalize_severity(info.get("severity"))
        name = info.get("name") or item.get("template-id") or "Nuclei Finding"
        matched_at = item.get("matched-at") or item.get("host")
        template_id = item.get("template-id")
        matcher_name = item.get("matcher-name")
        extracted_results = item.get("extracted-results")

        # Extract CVE ID from template-id or classification
        import re
        cve_id = None
        classification = info.get("classification") or {}
        cve_list = classification.get("cve-id") or []
        if isinstance(cve_list, list) and cve_list:
            cve_id = cve_list[0].upper()
        elif isinstance(cve_list, str) and cve_list:
            cve_id = cve_list.upper()
        if not cve_id and template_id:
            m = re.search(r"CVE-\d{4}-\d+", template_id, re.IGNORECASE)
            if m:
                cve_id = m.group(0).upper()

        evidence_parts: list[str] = []
        if template_id:
            evidence_parts.append(f"template={template_id}")
        if matched_at:
            evidence_parts.append(f"matched-at={matched_at}")
        if matcher_name:
            evidence_parts.append(f"matcher={matcher_name}")
        if extracted_results:
            evidence_parts.append(f"extracted={extracted_results}")

        results.append({
            "name": name,
            "severity": severity,
            "matched_at": matched_at,
            "template_id": template_id,
            "cve_id": cve_id,
            "matcher_name": matcher_name,
            "extracted_results": extracted_results,
            "evidence": " | ".join(evidence_parts) if evidence_parts else None,
        })

    return results
