"""
pipeline_task.py — Compound Reconnaissance Pipeline for RASID
==============================================================
يُشغِّل هذا الملف الأدوات الخمس بالتسلسل الصحيح:
  1. Amass + Subfinder  → جمع النطاقات الفرعية
  2. Masscan            → مسح المنافذ السريع
  3. Httpx              → التحقق من خدمات الويب
  4. Nmap               → فحص عميق للخدمات
  5. Nuclei             → كشف الثغرات

كيفية الإضافة للمشروع:
  - ضع هذا الملف في: backend/app/pipeline_task.py
  - أضف في scan_routes.py: from app.pipeline_task import run_pipeline
  - أضف endpoint: POST /api/scans/pipeline

الاستخدام من الـ API:
  POST /api/scans/pipeline
  Body: {"target": "example.com"}
"""
from __future__ import annotations

import socket
import re
from datetime import datetime, timezone
from typing import Any

from app.celery_app import celery
from app.db import SessionLocal
from app.logging_setup import logger
from app.models import (
    AssetType,
    FindingSeverity,
    ScanJob,
    ScanStatus,
)
from app.tools import persistence as P
from app.tools.registry import get_tool
from app.tools.runner import run_tool
from app.tools.parsers import (
    amass_parser,
    subfinder_parser,
    masscan_parser,
    httpx_parser,
    nmap_parser,
    nuclei_parser,
)
from app.aggregator import aggregate_target
from app.validation import validate_target


def _now():
    return datetime.now(timezone.utc)


def _update_status(db, job: ScanJob, status: str, note: str = "") -> None:
    """تحديث حالة الفحص وحفظها في قاعدة البيانات."""
    job.status = status
    if note:
        # نضيف الملاحظة إلى stdout ليراها المستخدم في الـ raw view
        job.stdout = (job.stdout or "") + f"\n[PIPELINE] {note}"
    db.commit()
    logger.info("Pipeline job=%s → %s  %s", job.id, status, note)


def _resolve_to_ip(hostname: str) -> str | None:
    """تحويل الاسم إلى IP لـ Masscan (لا يقبل أسماء نطاقات)."""
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
        return hostname
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror as e:
        logger.warning("Could not resolve %s: %s", hostname, e)
        return None


# ─── المرحلة 1: جمع النطاقات الفرعية ─────────────────────────────────────

def _stage_discovery(db, job: ScanJob, target: str) -> list[str]:
    """
    تشغيل Amass و Subfinder وجمع نتائجهما في قائمة موحدة.
    المخرج: قائمة بالنطاقات الفرعية المكتشفة (مشمولاً الهدف نفسه).
    """
    _update_status(db, job, ScanStatus.RUNNING.value,
                   "Stage 1/5 — Subdomain discovery (Amass + Subfinder)")

    discovered: set[str] = {target}  # نبدأ بالهدف الأصلي دائماً

    # ── Subfinder ──────────────────────────────────────────────────────────
    subfinder_spec = get_tool("subfinder")
    if subfinder_spec:
        sf_result = run_tool(subfinder_spec, target=target)
        job.stdout = (job.stdout or "") + "\n=== SUBFINDER ===\n" + sf_result.raw_text
        db.commit()
        for entry in subfinder_parser.parse(sf_result.raw_text):
            host = entry.get("host", "")
            if host:
                discovered.add(host)
                # حفظ الأصل في قاعدة البيانات
                asset = P.get_or_create_asset(db, AssetType.DOMAIN, host)
                P.link_scan_asset(db, job.id, asset.id, "SUBDOMAIN")
                P.create_finding(
                    db, scan_id=job.id, asset_id=asset.id,
                    title="Subdomain Discovered (Subfinder)",
                    severity=FindingSeverity.INFO.value,
                    description=f"Passive enumeration found: {host}",
                    confidence="medium",
                    evidence=f"source={entry.get('source', 'subfinder')}",
                    recommendation="Audit ownership of discovered subdomain.",
                )
    else:
        logger.warning("subfinder not registered — skipping")

    # ── Amass ──────────────────────────────────────────────────────────────
    amass_spec = get_tool("amass")
    if amass_spec:
        am_result = run_tool(amass_spec, target=target)
        job.stdout = (job.stdout or "") + "\n=== AMASS ===\n" + am_result.raw_text
        db.commit()
        for entry in amass_parser.parse(am_result.raw_text):
            host = entry.get("host", "")
            if host:
                discovered.add(host)
                asset = P.get_or_create_asset(db, AssetType.DOMAIN, host)
                P.link_scan_asset(db, job.id, asset.id, "SUBDOMAIN")
                for ip in entry.get("ips", []):
                    ip_asset = P.get_or_create_asset(db, AssetType.IP, ip)
                    P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")
                P.create_finding(
                    db, scan_id=job.id, asset_id=asset.id,
                    title="Subdomain Discovered (Amass)",
                    severity=FindingSeverity.INFO.value,
                    description=f"Amass enumerated: {host}",
                    confidence="medium",
                    evidence=f"ips={', '.join(entry.get('ips', []) or ['none'])}",
                    recommendation="Audit ownership and exposure of subdomain.",
                )
    else:
        logger.warning("amass not registered — skipping")

    db.commit()
    logger.info("Stage 1 done — discovered %d hosts", len(discovered))
    return list(discovered)


# ─── المرحلة 2: مسح المنافذ ───────────────────────────────────────────────

def _stage_masscan(db, job: ScanJob, hosts: list[str]) -> list[dict]:
    """
    تشغيل Masscan على الـ IPs المكتشفة.
    المخرج: قائمة بالمنافذ المفتوحة {ip, port, protocol, state, name}.
    """
    _update_status(db, job, ScanStatus.RUNNING.value,
                   f"Stage 2/5 — Port scan (Masscan) on {len(hosts)} host(s)")

    masscan_spec = get_tool("masscan")
    if not masscan_spec:
        logger.warning("masscan not registered — skipping port scan")
        return []

    open_ports: list[dict] = []

    # Masscan يقبل IP فقط — نحوّل الأسماء
    ip_to_host: dict[str, str] = {}
    for host in hosts:
        ip = _resolve_to_ip(host)
        if ip:
            ip_to_host[ip] = host

    if not ip_to_host:
        logger.warning("No resolvable IPs — skipping Masscan")
        return []

    # نشغّل Masscan على كل IP (يمكن تحسينه لاحقاً بـ input file)
    for ip, original_host in ip_to_host.items():
        ms_result = run_tool(masscan_spec, target=ip)
        job.stdout = (job.stdout or "") + f"\n=== MASSCAN ({ip}) ===\n" + ms_result.raw_text
        db.commit()

        if ms_result.exit_code != 0:
            logger.warning("Masscan failed for %s (exit %s)", ip, ms_result.exit_code)
            continue

        services = masscan_parser.parse(ms_result.raw_text)
        for s in services:
            ip_asset = P.get_or_create_asset(db, AssetType.IP, s["ip"])
            P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")

            svc = P.upsert_service(
                db, ip_asset.id,
                s["port"], s["protocol"], s["state"], s["name"],
            )
            P.link_scan_service(db, job.id, svc.id)

            severity = P.service_severity(svc.port)
            P.create_finding(
                db, scan_id=job.id, asset_id=ip_asset.id, service_id=svc.id,
                title="Open Port (Masscan)",
                severity=severity,
                description=f"Masscan found open port {s['port']}/{s['protocol']} on {s['ip']}",
                confidence="medium",
                evidence=f"{s['ip']}:{s['port']}/{s['protocol']}",
                recommendation="Verify the service on this port and restrict if unneeded.",
                port=svc.port,
            )
            open_ports.append({**s, "original_host": original_host})

    db.commit()
    logger.info("Stage 2 done — found %d open ports", len(open_ports))
    return open_ports


# ─── المرحلة 3: التحقق من خدمات الويب ────────────────────────────────────

def _stage_httpx(db, job: ScanJob, hosts: list[str]) -> list[dict]:
    """
    تشغيل Httpx للتحقق من خدمات HTTP/HTTPS.
    المخرج: قائمة بالـ endpoints الحية {url, host, port, status_code, ...}.
    """
    _update_status(db, job, ScanStatus.RUNNING.value,
                   f"Stage 3/5 — HTTP probe (Httpx) on {len(hosts)} host(s)")

    httpx_spec = get_tool("httpx")
    if not httpx_spec:
        logger.warning("httpx not registered — skipping HTTP verification")
        return []

    alive_endpoints: list[dict] = []

    for host in hosts:
        hx_result = run_tool(httpx_spec, target=host)
        job.stdout = (job.stdout or "") + f"\n=== HTTPX ({host}) ===\n" + hx_result.raw_text
        db.commit()

        if hx_result.exit_code != 0:
            continue

        endpoints = httpx_parser.parse(hx_result.raw_text)
        for ep in endpoints:
            ep_host = ep.get("host") or host
            asset_type = P.guess_asset_type(ep_host)
            asset = P.get_or_create_asset(db, asset_type, ep_host)

            endpoint = P.upsert_web_endpoint(
                db,
                asset_id=asset.id,
                url=ep["url"],
                scheme=ep.get("scheme", "http"),
                host=ep_host,
                port=ep.get("port"),
                path=ep.get("path", "/"),
                status_code=ep.get("status_code"),
                title=ep.get("title"),
                webserver=ep.get("webserver"),
            )
            P.link_scan_web_endpoint(db, job.id, endpoint.id)
            P.create_finding(
                db, scan_id=job.id, asset_id=asset.id,
                web_endpoint_id=endpoint.id,
                title="Reachable Web Endpoint",
                severity=FindingSeverity.INFO.value,
                description=f"Live web endpoint at {ep['url']}",
                confidence="high",
                evidence=f"HTTP {ep.get('status_code')} | title={ep.get('title')} | server={ep.get('webserver')}",
                recommendation="Ensure endpoint is intended to be public.",
                has_web=True,
            )
            alive_endpoints.append(ep)

    db.commit()
    logger.info("Stage 3 done — found %d live web endpoints", len(alive_endpoints))
    return alive_endpoints


# ─── المرحلة 4: الفحص العميق بـ Nmap ─────────────────────────────────────

def _stage_nmap(db, job: ScanJob, hosts: list[str]) -> None:
    """
    تشغيل Nmap للفحص العميق واستخراج معلومات الخدمات وإصداراتها.
    """
    _update_status(db, job, ScanStatus.RUNNING.value,
                   f"Stage 4/5 — Deep scan (Nmap) on {len(hosts)} host(s)")

    nmap_spec = get_tool("nmap")
    if not nmap_spec:
        logger.warning("nmap not registered — skipping deep scan")
        return

    for host in hosts:
        nm_result = run_tool(nmap_spec, target=host)
        job.stdout = (job.stdout or "") + f"\n=== NMAP ({host}) ===\n" + nm_result.raw_text
        db.commit()

        if nm_result.exit_code != 0:
            logger.warning("Nmap failed for %s (exit %s)", host, nm_result.exit_code)
            continue

        parsed = nmap_parser.parse(nm_result.raw_text)

        target_type = P.guess_asset_type(host)
        target_asset = P.get_or_create_asset(db, target_type, host)
        P.link_scan_asset(db, job.id, target_asset.id, "TARGET")

        ip_assets = []
        for ip in parsed.get("ips", []):
            ip_asset = P.get_or_create_asset(db, AssetType.IP, ip)
            ip_assets.append(ip_asset)
            P.link_scan_asset(db, job.id, ip_asset.id, "RESOLVED_IP")

        primary_ip_asset = ip_assets[0] if ip_assets else target_asset

        for s in parsed.get("services", []):
            svc = P.upsert_service(
                db, primary_ip_asset.id,
                s["port"], s["protocol"], s["state"], s["name"],
            )
            P.link_scan_service(db, job.id, svc.id)
            severity = P.service_severity(svc.port)
            P.create_finding(
                db, scan_id=job.id,
                asset_id=primary_ip_asset.id,
                service_id=svc.id,
                title="Open Service Detected (Nmap)",
                severity=severity,
                description=(
                    f"Nmap detected {svc.name} on port {svc.port}/{svc.protocol} "
                    f"(state={svc.state}) on {host}."
                ),
                confidence="high",
                evidence=f"{svc.port}/{svc.protocol} {svc.state} {svc.name}",
                recommendation="Review whether this service should be publicly exposed.",
                port=svc.port,
            )

    db.commit()
    logger.info("Stage 4 (Nmap) done for %d hosts", len(hosts))


# ─── المرحلة 5: كشف الثغرات بـ Nuclei ────────────────────────────────────

def _stage_nuclei(db, job: ScanJob, alive_endpoints: list[dict]) -> list[str]:
    """
    تشغيل Nuclei على الـ URLs الحية لكشف الثغرات المعروفة.
    المخرج: قائمة بمستويات الخطورة المكتشفة (لتشغيل الإشعارات).
    """
    if not alive_endpoints:
        logger.info("No live endpoints for Nuclei — skipping")
        return []

    urls = list({ep["url"] for ep in alive_endpoints if ep.get("url")})
    _update_status(db, job, ScanStatus.RUNNING.value,
                   f"Stage 5/5 — Vulnerability scan (Nuclei) on {len(urls)} URL(s)")

    nuclei_spec = get_tool("nuclei")
    if not nuclei_spec:
        logger.warning("nuclei not registered — skipping vuln scan")
        return []

    severities_seen: list[str] = []

    for url in urls:
        nu_result = run_tool(nuclei_spec, target=url)
        job.stdout = (job.stdout or "") + f"\n=== NUCLEI ({url}) ===\n" + nu_result.raw_text
        db.commit()

        # nuclei: exit 0 = نتائج, exit 1 = لا نتائج, exit 2+ = خطأ
        has_output = any(
            line.strip().startswith("{")
            for line in nu_result.raw_text.splitlines()
        )
        if nu_result.exit_code > 1 and not has_output:
            logger.warning("Nuclei error for %s (exit %s)", url, nu_result.exit_code)
            continue

        target_type = P.guess_asset_type(url)
        target_asset = P.get_or_create_asset(db, target_type, url)

        for finding in nuclei_parser.parse(nu_result.raw_text):
            severities_seen.append(finding["severity"])
            cve_prefix = f"{finding['cve_id']} — " if finding.get("cve_id") else ""
            P.create_finding(
                db, scan_id=job.id,
                asset_id=target_asset.id,
                title=finding["name"],
                severity=finding["severity"],
                description=(
                    f"{cve_prefix}Nuclei identified a potential issue "
                    f"on {finding.get('matched_at') or url}."
                ),
                confidence="high",
                evidence=finding["evidence"],
                recommendation=(
                    "Validate and remediate per the affected technology "
                    "and Nuclei template guidance."
                ),
                has_web=True,
            )

    db.commit()
    logger.info("Stage 5 (Nuclei) done — severities seen: %s", severities_seen)
    return severities_seen


# ─── Celery Task الرئيسي ───────────────────────────────────────────────────

@celery.task(name="run_pipeline_scan")
def run_pipeline_scan(scan_id: int) -> dict[str, Any]:
    """
    الـ Celery task الرئيسي للـ pipeline المركب.
    يُستدعى من scan_routes.py عبر: run_pipeline_scan.delay(job.id)
    """
    db = SessionLocal()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == scan_id).one_or_none()
        if not job:
            return {"ok": False, "error": "ScanJob not found"}

        # ── التحقق من الهدف ──────────────────────────────────────────────
        validation = validate_target(job.target)
        if not validation.ok:
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Invalid target: {validation.reason}"
            job.finished_at = _now()
            db.commit()
            logger.warning("Pipeline scan %s rejected: %s", scan_id, validation.reason)
            return {"ok": False, "error": job.error_message}

        target = job.target
        job.started_at = _now()
        db.commit()

        # حفظ الهدف الأصلي كـ asset
        target_asset_type = P.guess_asset_type(target)
        target_asset = P.get_or_create_asset(db, target_asset_type, target)
        P.link_scan_asset(db, job.id, target_asset.id, "TARGET")
        db.commit()

        # ── المرحلة 1: جمع النطاقات ──────────────────────────────────────
        all_hosts = _stage_discovery(db, job, target)

        # ── المرحلة 2: مسح المنافذ ───────────────────────────────────────
        open_ports = _stage_masscan(db, job, all_hosts)

        # ── المرحلة 3: التحقق من الويب ───────────────────────────────────
        alive_endpoints = _stage_httpx(db, job, all_hosts)

        # ── المرحلة 4: الفحص العميق ──────────────────────────────────────
        # نركز Nmap على الهدف الأصلي + الـ hosts التي وجدنا لها منافذ
        nmap_targets = list({port["original_host"] for port in open_ports} | {target})
        _stage_nmap(db, job, nmap_targets)

        # ── المرحلة 5: كشف الثغرات ───────────────────────────────────────
        severities = _stage_nuclei(db, job, alive_endpoints)

        # ── إنهاء الـ pipeline ────────────────────────────────────────────
        job.status = ScanStatus.SUCCESS.value
        job.finished_at = _now()
        job.stdout = (job.stdout or "") + "\n[PIPELINE] All stages completed successfully."
        db.commit()

        # تجميع النتائج
        try:
            aggregate_target(db, target)
        except Exception as agg_err:
            logger.warning("Aggregation failed for %s: %s", target, agg_err)

        # إشعارات للثغرات الحرجة
        from app.tasks import _maybe_notify
        _maybe_notify(db, job, severities)
        db.commit()

        return {
            "ok": True,
            "scan_id": job.id,
            "target": target,
            "pipeline_stages": 5,
            "hosts_discovered": len(all_hosts),
            "open_ports_found": len(open_ports),
            "live_endpoints": len(alive_endpoints),
            "severities_found": severities,
        }

    except Exception as e:
        logger.exception("Pipeline scan %s raised", scan_id)
        try:
            job.status = ScanStatus.FAILED.value
            job.error_message = f"Pipeline error ({type(e).__name__})"
            job.finished_at = _now()
            db.commit()
        except Exception:
            pass
        return {"ok": False, "scan_id": scan_id, "error": str(e)}
    finally:
        db.close()
