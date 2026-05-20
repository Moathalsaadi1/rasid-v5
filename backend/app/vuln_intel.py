"""
Vulnerability Intelligence — fetches CVE data from NVD API with DB caching.
Cache TTL: 24 hours. Rate limit: 1 request / 6 seconds (NVD free tier).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.logging_setup import logger
from app.models import VulnCache

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CACHE_TTL_HOURS = 24
RATE_LIMIT_SECONDS = 6  # NVD free tier: max 5 req / 30s


def _is_fresh(fetched_at: datetime) -> bool:
    age = datetime.now(timezone.utc) - fetched_at
    return age < timedelta(hours=CACHE_TTL_HOURS)


def _fetch_from_nvd(cve_id: str) -> dict | None:
    """Fetch CVE data from NVD API."""
    try:
        time.sleep(RATE_LIMIT_SECONDS)
        resp = requests.get(
            NVD_API_URL,
            params={"cveId": cve_id},
            timeout=15,
            headers={"User-Agent": "RASID-Educational-Tool/1.0"},
        )
        if resp.status_code != 200:
            logger.warning("NVD API returned %s for %s", resp.status_code, cve_id)
            return None

        data = resp.json()
        vulns = data.get("vulnerabilities", [])
        if not vulns:
            return None

        return vulns[0].get("cve", {})
    except Exception as e:
        logger.error("NVD fetch failed for %s: %s", cve_id, e)
        return None


def _parse_nvd(cve: dict) -> dict:
    """Extract the fields we need for educational display."""
    # Description
    descriptions = cve.get("descriptions", [])
    desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "No description available.")

    # CVSS Score
    metrics = cve.get("metrics", {})
    score = None
    severity = None
    vector = None

    for version in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
        items = metrics.get(version, [])
        if items:
            cvss = items[0].get("cvssData", {})
            score    = cvss.get("baseScore")
            severity = cvss.get("baseSeverity") or items[0].get("baseSeverity")
            vector   = cvss.get("vectorString")
            break

    # CWE
    weaknesses = cve.get("weaknesses", [])
    cwes = []
    for w in weaknesses:
        for desc_item in w.get("description", []):
            val = desc_item.get("value", "")
            if val.startswith("CWE-"):
                cwes.append(val)

    # References
    refs = [r.get("url") for r in cve.get("references", [])[:5] if r.get("url")]

    # Published date
    published = cve.get("published", "")[:10] if cve.get("published") else None

    return {
        "cve_id":      cve.get("id"),
        "description": desc,
        "score":       score,
        "severity":    severity,
        "vector":      vector,
        "cwes":        cwes,
        "references":  refs,
        "published":   published,
        "source":      "NVD",
    }


def get_vuln_intel(db: Session, cve_id: str) -> Optional[dict]:
    """
    Returns educational CVE data.
    Checks DB cache first; fetches from NVD if stale or missing.
    """
    cve_id = cve_id.upper().strip()
    if not cve_id.startswith("CVE-"):
        return None

    # Check cache
    cached = db.query(VulnCache).filter_by(cve_id=cve_id).one_or_none()
    if cached and _is_fresh(cached.fetched_at):
        logger.debug("Cache hit for %s", cve_id)
        return json.loads(cached.data)

    # Fetch from NVD
    logger.info("Fetching %s from NVD", cve_id)
    raw = _fetch_from_nvd(cve_id)
    if not raw:
        return None

    parsed = _parse_nvd(raw)

    # Save to cache
    if cached:
        cached.data = json.dumps(parsed)
        cached.fetched_at = datetime.now(timezone.utc)
    else:
        db.add(VulnCache(cve_id=cve_id, data=json.dumps(parsed)))
    db.commit()

    return parsed
