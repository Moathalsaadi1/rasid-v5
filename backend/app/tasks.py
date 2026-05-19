"""
Celery tasks — one task per supported tool.

Each task has a uniform shape:
  1. Mark the scan RUNNING.
  2. Validate the target.
  3. Run the tool via app.tools.runner.run_tool().
  4. Parse output via app.tools.parsers.<tool>_parser.parse().
  5. Persist Assets / Services / WebEndpoints / Findings via persistence helpers.
  6. Mark the scan SUCCESS or FAILED.
  7. Hand off to the notifications module for HIGH/CRITICAL findings.

If you need to add a new tool, register it in app.tools.registry and add a
parser; you should rarely need to add new code here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from app.celery_app import celery
from app.db import SessionLocal
from app.logging_setup import logger
from app.models import (
    AssetType,
    FindingSeverity,
    ScanJob,
    ScanStatus,
)
from app.tools.parsers import (
    amass_parser,
    httpx_parser,
    masscan_parser,
    massdns_parser,
    nmap_parser,
    nuclei_parser,
    subfinder_parser,
)
from app.tools import persistence as P
from app.tools.registry import get_tool
from app.tools.runner import run_tool
from app.validation import validate_target


# ─── Module-level helpers (kept for back-compat with existing imports) ─────

def _now():
    return datetime.now(timezone.utc)


def _is_safe_target(target: str) -> bool:
    return bool(validate_target(target))


# ─── Custom command resolution ─────────────────────────────────────────────

def _resolve_args(db, user_id: int | None, tool_name: str) -> list[str] | None:
    """Returns the user's saved custom args for this tool, if any.

    The UserToolCommand model is added in Phase 3; we import it lazily so
    this file keeps working in the (transient) state where the migration
    hasn't been run yet.
    """
    if user_id is None:
        return None
    try:
        from app.models import UserToolCommand  # noqa: WPS433
    except ImportError:
        return None

    row = (
        db.query(UserToolCommand)
        .filter(
            UserToolCommand.user_id == user_id,
            UserToolCommand.tool_name == tool_name,
            UserToolCommand.is_active.is_(True),
        )
        .one_or_none()
    )
    if not row or not row.args:
        return None

    import json
    try:
        parsed = json.loads(row.args)
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "Invalid custom args for user=%s tool=%s — falling back to defaults",
            user_id, tool_name,
        )
        return None

    if not (isinstance(parsed, list) and all(isinstance(x, str) for x in parsed)):
        logger.warning(
            "Custom args for user=%s tool=%s not a list of strings — ignored",
            user_id, tool_name,
        )
        return None

    # Merge with defaults: start from spec.default_args and append any
    # user-supplied arg not already present. This makes "user adds -sV to
    # nmap" produce "-T3 -F -oX - -sV" instead of just "-sV".
    spec = get_tool(tool_name)
    if not spec:
        return parsed

    merged = list(spec.default_args)
    for arg in parsed:
        if arg not in merged:
            merged.append(arg)

    return merged


# ─── Notification trigger ─────────────────────────────────────────────────

def _maybe_notify(db, scan: ScanJob, severities_seen: list[str]) -> None:
    """Create a notification row when the scan produced HIGH/CRITICAL findings."""
    if not scan.user_id:
        return
    high_or_critical = {"high", "critical"} & set(severities_seen)
    if not high_or_critical:
        return
    try:
        from app.models import Notification  # noqa: WPS433
    except ImportError:
        return
    top_severity = "critical" if "critical" in high_or_critical else "high"
    note = Notification(
        user_id=scan.user_id,
        scan_id=scan.id,
        severity=top_severity,
        title=f"Scan #{scan.id} found {top_severity} issues",
        message=f"Target: {scan.target} • Tool: {scan.tool}",
    )
    db.add(note)


# ─── Generic scan wrapper ─────────────────────────────────────────────────

def _run_scan_task(
    scan_id: int,
    tool_name: str,
    handler: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Wraps every tool task with the same lifecycle (status transitions,
    target validation, exception handling)."""
    db = SessionLocal()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == scan_id).one_or_none()
        if not job:
            return {"ok": False, "error": "ScanJob not found"}

        result = validate_target(job.target)
        if not result.ok:
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Invalid target: {result.reason}"
            job.finished_at = _now()
            db.commit()
            logger.warning("Scan %s rejected: %s", scan_id, result.reason)
            return {"ok": False, "error": job.error_message}

        job.status = ScanStatus.RUNNING.value
        job.started_at = _now()
        db.commit()

        spec = get_tool(tool_name)
        if not spec:
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Unknown tool: {tool_name}"
            job.finished_at = _now()
            db.commit()
            return {"ok": False, "error": job.error_message}

        custom_args = _resolve_args(db, job.user_id, tool_name)

        try:
            return handler(db=db, job=job, spec=spec, custom_args=custom_args)
        except Exception as e:  # noqa: BLE001
            # Full traceback to the server log only — the client just gets
            # the exception class name. Surfacing str(e) verbatim would
            # leak file paths, DB queries, or container internals.
            logger.exception("Scan %s (%s) raised", scan_id, tool_name)
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Internal error ({type(e).__name__})"
            job.finished_at = _now()
            db.commit()
            return {"ok": False, "scan_id": scan_id, "error": job.error_message}

    finally:
        db.close()


# ─── nmap ────────────────────────────────────────────────────────────────

def _handle_nmap(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    result = run_tool(spec, target=job.target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"nmap exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    parsed = nmap_parser.parse(result.raw_text)

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    for domain in parsed["domains"]:
        d_asset = P.get_or_create_asset(db, AssetType.DOMAIN, domain)
        P.link_scan_asset(db, job.id, d_asset.id, "OUTPUT_DOMAIN")

    ip_assets = []
    for ip in parsed["ips"]:
        ip_asset = P.get_or_create_asset(db, AssetType.IP, ip)
        ip_assets.append(ip_asset)
        P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")

    primary_ip_asset = ip_assets[0] if ip_assets else None
    findings_count = 0
    severities: list[str] = []

    if primary_ip_asset:
        for s in parsed["services"]:
            svc = P.upsert_service(
                db, primary_ip_asset.id,
                s["port"], s["protocol"], s["state"], s["name"],
            )
            P.link_scan_service(db, job.id, svc.id)

            severity = P.service_severity(svc.port)
            severities.append(severity)
            P.create_finding(
                db, scan_id=job.id,
                asset_id=primary_ip_asset.id,
                service_id=svc.id,
                title="Open Service Detected",
                severity=severity,
                description=f"An open {svc.protocol.upper()} service was detected on port {svc.port} ({svc.name}).",
                confidence="high",
                evidence=f"{svc.port}/{svc.protocol} {svc.state} {svc.name}",
                recommendation="Review whether this service should be publicly exposed. Restrict access if not required.",
                port=svc.port,
            )
            findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    _maybe_notify(db, job, severities)
    db.commit()

    return {
        "ok": True, "scan_id": job.id,
        "domains_count": len(parsed["domains"]),
        "ips_count": len(parsed["ips"]),
        "services_count": len(parsed["services"]),
        "findings_count": findings_count,
    }


@celery.task(name="run_nmap_scan")
def run_nmap_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "nmap", _handle_nmap)


# ─── httpx ──────────────────────────────────────────────────────────────────

def _handle_httpx(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    result = run_tool(spec, target=job.target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"httpx exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    endpoints = httpx_parser.parse(result.raw_text)
    findings_count = 0
    severities: list[str] = []

    for ep in endpoints:
        host = ep["host"] or job.target
        asset_type = P.guess_asset_type(host)
        asset = P.get_or_create_asset(db, asset_type, host)

        endpoint = P.upsert_web_endpoint(
            db,
            asset_id=asset.id,
            url=ep["url"],
            scheme=ep["scheme"],
            host=host,
            port=ep["port"],
            path=ep["path"],
            status_code=ep["status_code"],
            title=ep["title"],
            webserver=ep["webserver"],
        )
        P.link_scan_web_endpoint(db, job.id, endpoint.id)

        severities.append(FindingSeverity.INFO.value)
        P.create_finding(
            db, scan_id=job.id,
            asset_id=asset.id,
            web_endpoint_id=endpoint.id,
            title="Reachable Web Endpoint",
            severity=FindingSeverity.INFO.value,
            description=f"A reachable web endpoint was discovered at {ep['url']}.",
            confidence="high",
            evidence=f"HTTP {ep['status_code']} | title={ep['title']} | server={ep['webserver']}",
            recommendation="Review whether this web endpoint is expected and properly protected.",
            has_web=True,
        )
        findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    _maybe_notify(db, job, severities)
    db.commit()

    return {"ok": True, "scan_id": job.id,
            "web_endpoints_count": len(endpoints),
            "findings_count": findings_count}


@celery.task(name="run_httpx_scan")
def run_httpx_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "httpx", _handle_httpx)


# ─── nuclei ────────────────────────────────────────────────────────────────

def _handle_nuclei(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    result = run_tool(spec, target=job.target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    # nuclei: exit 0 = success with findings, 1 = success without findings, 2+ = error
    has_output = any(line.strip().startswith("{") for line in result.raw_text.splitlines())
    if result.exit_code > 1 and not has_output:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"nuclei exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    findings = nuclei_parser.parse(result.raw_text)
    severities: list[str] = []

    for f in findings:
        severities.append(f["severity"])
        P.create_finding(
            db, scan_id=job.id,
            asset_id=target_asset.id,
            title=f["name"],
            severity=f["severity"],
            description=f"Nuclei identified a potential issue on {f.get('matched_at') or job.target}.",
            confidence="high",
            evidence=f["evidence"],
            recommendation="Validate the finding and remediate according to the affected technology and template guidance.",
            has_web=True,
        )

    job.status = ScanStatus.SUCCESS.value
    _maybe_notify(db, job, severities)
    db.commit()

    return {"ok": True, "scan_id": job.id, "findings_count": len(findings)}


@celery.task(name="run_nuclei_scan")
def run_nuclei_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "nuclei", _handle_nuclei)


# ─── subfinder ─────────────────────────────────────────────────────────────

def _handle_subfinder(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    result = run_tool(spec, target=job.target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"subfinder exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    subdomains = subfinder_parser.parse(result.raw_text)
    findings_count = 0

    for entry in subdomains:
        host = entry["host"]
        sub_asset = P.get_or_create_asset(db, AssetType.DOMAIN, host)
        P.link_scan_asset(db, job.id, sub_asset.id, "SUBDOMAIN")

        P.create_finding(
            db, scan_id=job.id,
            asset_id=sub_asset.id,
            title="Subdomain Discovered",
            severity=FindingSeverity.INFO.value,
            description=f"Passive enumeration discovered subdomain {host}.",
            confidence="medium",
            evidence=f"source={entry.get('source') or 'subfinder'}",
            recommendation="Verify that the subdomain is intended to be public; orphan subdomains can lead to takeover.",
        )
        findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    db.commit()

    return {"ok": True, "scan_id": job.id,
            "subdomains_count": len(subdomains),
            "findings_count": findings_count}


@celery.task(name="run_subfinder_scan")
def run_subfinder_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "subfinder", _handle_subfinder)


# ─── amass ─────────────────────────────────────────────────────────────────

def _handle_amass(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    result = run_tool(spec, target=job.target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"amass exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    discovered = amass_parser.parse(result.raw_text)
    findings_count = 0

    for entry in discovered:
        host = entry["host"]
        sub_asset = P.get_or_create_asset(db, AssetType.DOMAIN, host)
        P.link_scan_asset(db, job.id, sub_asset.id, "SUBDOMAIN")

        for ip in entry.get("ips", []):
            ip_asset = P.get_or_create_asset(db, AssetType.IP, ip)
            P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")

        sources = ", ".join(entry.get("sources") or []) or "amass"
        P.create_finding(
            db, scan_id=job.id,
            asset_id=sub_asset.id,
            title="Subdomain Discovered (Amass)",
            severity=FindingSeverity.INFO.value,
            description=f"Amass enumerated subdomain {host}.",
            confidence="medium",
            evidence=f"sources={sources} | ips={', '.join(entry.get('ips') or []) or 'none'}",
            recommendation="Audit ownership and exposure of every discovered subdomain.",
        )
        findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    db.commit()

    return {"ok": True, "scan_id": job.id,
            "subdomains_count": len(discovered),
            "findings_count": findings_count}


@celery.task(name="run_amass_scan")
def run_amass_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "amass", _handle_amass)


# ─── masscan ───────────────────────────────────────────────────────────────

def _handle_masscan(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    # masscan only accepts IP addresses, not hostnames — resolve if needed.
    import socket, re
    target = job.target
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target):
        try:
            target = socket.gethostbyname(job.target)
            logger.info("Resolved %s -> %s for masscan", job.target, target)
        except socket.gaierror as e:
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Could not resolve hostname '{job.target}': {e}"
            job.finished_at = _now()
            db.commit()
            return {"ok": False, "scan_id": job.id, "error": job.error_message}

    result = run_tool(spec, target=target, args=custom_args)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"masscan exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    services = masscan_parser.parse(result.raw_text)
    findings_count = 0
    severities: list[str] = []

    ip_to_asset: dict[str, Any] = {}
    for s in services:
        ip = s["ip"]
        if ip not in ip_to_asset:
            ip_to_asset[ip] = P.get_or_create_asset(db, AssetType.IP, ip)
            P.link_scan_asset(db, job.id, ip_to_asset[ip].id, "RESOLVED_IP")

        ip_asset = ip_to_asset[ip]
        svc = P.upsert_service(
            db, ip_asset.id,
            s["port"], s["protocol"], s["state"], s["name"],
        )
        P.link_scan_service(db, job.id, svc.id)

        severity = P.service_severity(svc.port)
        severities.append(severity)
        P.create_finding(
            db, scan_id=job.id,
            asset_id=ip_asset.id,
            service_id=svc.id,
            title="Open Port (Masscan)",
            severity=severity,
            description=f"Masscan reported port {svc.port}/{svc.protocol} as {svc.state}.",
            confidence="medium",
            evidence=f"{ip}:{svc.port}/{svc.protocol}",
            recommendation="Confirm the service running on this port and assess whether it should be exposed.",
            port=svc.port,
        )
        findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    _maybe_notify(db, job, severities)
    db.commit()

    return {"ok": True, "scan_id": job.id,
            "services_count": len(services),
            "findings_count": findings_count}


@celery.task(name="run_masscan_scan")
def run_masscan_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "masscan", _handle_masscan)


# ─── massdns ───────────────────────────────────────────────────────────────

def _handle_massdns(*, db, job: ScanJob, spec, custom_args) -> dict[str, Any]:
    stdin = job.target + "\n"
    result = run_tool(spec, target=job.target, args=custom_args, stdin_data=stdin)
    job.stdout = result.raw_text
    job.stderr = result.stderr
    job.finished_at = _now()

    if result.exit_code != 0:
        job.status = ScanStatus.FAILED.value
        job.error_message = f"massdns exit code: {result.exit_code}"
        db.commit()
        return {"ok": False, "scan_id": job.id, "error": job.error_message}

    target_type = P.guess_asset_type(job.target)
    target_asset = P.get_or_create_asset(db, target_type, job.target)
    P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

    records = massdns_parser.parse(result.raw_text)
    findings_count = 0

    for rec in records:
        for ip in rec.get("ips", []):
            ip_asset = P.get_or_create_asset(db, AssetType.IP, ip)
            P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")

        P.create_finding(
            db, scan_id=job.id,
            asset_id=target_asset.id,
            title="DNS Resolution",
            severity=FindingSeverity.INFO.value,
            description=f"Resolved {rec['host']} → {', '.join(rec.get('ips') or []) or 'no records'} (status={rec.get('status')}).",
            confidence="high",
            evidence=f"status={rec.get('status')} | ips={', '.join(rec.get('ips') or []) or 'none'}",
            recommendation="Confirm DNS records match the intended public configuration.",
        )
        findings_count += 1

    job.status = ScanStatus.SUCCESS.value
    db.commit()

    return {"ok": True, "scan_id": job.id,
            "records_count": len(records),
            "findings_count": findings_count}


@celery.task(name="run_massdns_scan")
def run_massdns_scan(scan_id: int) -> dict:
    return _run_scan_task(scan_id, "massdns", _handle_massdns)


# ─── Tool dispatcher ───────────────────────────────────────────────────────

TASK_DISPATCH = {
    "nmap": run_nmap_scan,
    "httpx": run_httpx_scan,
    "nuclei": run_nuclei_scan,
    "subfinder": run_subfinder_scan,
    "amass": run_amass_scan,
    "masscan": run_masscan_scan,
    "massdns": run_massdns_scan,
}
