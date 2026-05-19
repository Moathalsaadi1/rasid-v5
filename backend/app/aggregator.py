from __future__ import annotations
import json
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.logging_setup import logger
from app.models import (
    AggregatedResult, Asset, AssetType, Finding, ScanJob, ScanStatus,
    Service, WebEndpoint, ScanAsset, ScanService, ScanWebEndpoint,
)
SUBDOMAIN_TOOLS = {"subfinder", "amass", "massdns"}
PORT_TOOLS      = {"nmap", "masscan"}
HTTP_TOOLS      = {"httpx"}
VULN_TOOLS      = {"nuclei"}

def _upsert(db, *, target, category, value, source, meta=None):
    now = datetime.now(timezone.utc)
    db.execute(text("""
        INSERT INTO aggregated_results
            (target, category, value, sources, confidence, meta, first_seen, last_seen)
        VALUES (:target, :category, :value,
                jsonb_build_array(:source)::text, :conf, :meta, :now, :now)
        ON CONFLICT (target, category, value) DO UPDATE SET
            sources = CASE
                WHEN aggregated_results.sources::jsonb @> jsonb_build_array(:source)
                THEN aggregated_results.sources
                ELSE (aggregated_results.sources::jsonb || jsonb_build_array(:source))::text
            END,
            confidence = CASE
                WHEN NOT (aggregated_results.sources::jsonb @> jsonb_build_array(:source))
                THEN CASE
                    WHEN jsonb_array_length(aggregated_results.sources::jsonb)+1 >= 3 THEN 'high'
                    WHEN jsonb_array_length(aggregated_results.sources::jsonb)+1 = 2  THEN 'medium'
                    ELSE 'low' END
                ELSE aggregated_results.confidence END,
            meta = :meta, last_seen = :now
    """), {"target": target, "category": category, "value": value,
           "source": source, "conf": "low",
           "meta": json.dumps(meta or {}), "now": now})

def aggregate_target(db: Session, target: str) -> int:
    logger.info("Aggregating results for target: %s", target)
    scans = db.query(ScanJob).filter(
        ScanJob.target == target,
        ScanJob.status == ScanStatus.SUCCESS.value).all()
    scan_ids     = [s.id for s in scans]
    tool_by_scan = {s.id: s.tool for s in scans}
    if not scan_ids:
        return 0

    subdomain_scans = [sid for sid in scan_ids if tool_by_scan[sid] in SUBDOMAIN_TOOLS]
    if subdomain_scans:
        rows = (db.query(ScanAsset, Asset)
            .join(Asset, ScanAsset.asset_id == Asset.id)
            .filter(ScanAsset.scan_id.in_(subdomain_scans),
                    Asset.type == AssetType.DOMAIN.value).all())
        for sa, asset in rows:
            _upsert(db, target=target, category="subdomain",
                    value=asset.value, source=tool_by_scan[sa.scan_id])

    port_scans = [sid for sid in scan_ids if tool_by_scan[sid] in PORT_TOOLS]
    if port_scans:
        rows = (db.query(ScanService, Service, Asset)
            .join(Service, ScanService.service_id == Service.id)
            .join(Asset, Service.ip_asset_id == Asset.id)
            .filter(ScanService.scan_id.in_(port_scans)).all())
        for ss, service, asset in rows:
            _upsert(db, target=target, category="port",
                    value=f"{asset.value}:{service.port}/{service.protocol}",
                    source=tool_by_scan[ss.scan_id],
                    meta={"service": service.name, "state": service.state})

    http_scans = [sid for sid in scan_ids if tool_by_scan[sid] in HTTP_TOOLS]
    if http_scans:
        rows = (db.query(ScanWebEndpoint, WebEndpoint)
            .join(WebEndpoint, ScanWebEndpoint.web_endpoint_id == WebEndpoint.id)
            .filter(ScanWebEndpoint.scan_id.in_(http_scans)).all())
        for se, ep in rows:
            _upsert(db, target=target, category="http_endpoint",
                    value=ep.url, source=tool_by_scan[se.scan_id],
                    meta={"status_code": ep.status_code,
                          "title": ep.title, "webserver": ep.webserver})

    vuln_scans = [sid for sid in scan_ids if tool_by_scan[sid] in VULN_TOOLS]
    if vuln_scans:
        for f in db.query(Finding).filter(Finding.scan_id.in_(vuln_scans)).all():
            _upsert(db, target=target, category="vulnerability",
                    value=f.title, source="nuclei",
                    meta={"severity": f.severity, "description": f.description,
                          "recommendation": f.recommendation})

    db.commit()
    count = db.query(AggregatedResult).filter_by(target=target).count()
    logger.info("Aggregation done for %s — %d unique results", target, count)
    return count
