"""
Shared helpers used by every Celery scan task.

Centralises:
  * risk-score calculation
  * Asset/ScanAsset upsert
  * Service/WebEndpoint upsert
  * Finding creation

Each scan task should *only* contain tool-specific orchestration logic and
delegate persistence to these helpers — this keeps the tasks short and
avoids subtle bugs from duplicated upsert code.
"""
from __future__ import annotations

import ipaddress
from typing import Optional

from app.models import (
    Asset,
    AssetType,
    Finding,
    FindingSeverity,
    ScanAsset,
    ScanService,
    ScanWebEndpoint,
    Service,
    WebEndpoint,
)


# ─── Asset helpers ─────────────────────────────────────────────────────────

def guess_asset_type(value: str) -> AssetType:
    try:
        ipaddress.ip_address(value)
        return AssetType.IP
    except ValueError:
        return AssetType.DOMAIN


def get_or_create_asset(db, asset_type: AssetType, value: str) -> Asset:
    existing = (
        db.query(Asset)
        .filter(Asset.type == asset_type.value, Asset.value == value)
        .one_or_none()
    )
    if existing:
        return existing

    asset = Asset(type=asset_type.value, value=value)
    db.add(asset)
    db.flush()
    return asset


def link_scan_asset(db, scan_id: int, asset_id: int, role: str) -> None:
    exists = (
        db.query(ScanAsset)
        .filter(
            ScanAsset.scan_id == scan_id,
            ScanAsset.asset_id == asset_id,
            ScanAsset.role == role,
        )
        .one_or_none()
    )
    if not exists:
        db.add(ScanAsset(scan_id=scan_id, asset_id=asset_id, role=role))


# ─── Service helpers ───────────────────────────────────────────────────────

def upsert_service(
    db,
    ip_asset_id: int,
    port: int,
    protocol: str,
    state: str,
    name: str,
) -> Service:
    svc = (
        db.query(Service)
        .filter(
            Service.ip_asset_id == ip_asset_id,
            Service.port == port,
            Service.protocol == protocol,
        )
        .one_or_none()
    )
    if svc:
        svc.state = state
        svc.name = name
        db.flush()
        return svc

    svc = Service(
        ip_asset_id=ip_asset_id,
        port=port,
        protocol=protocol,
        state=state,
        name=name,
    )
    db.add(svc)
    db.flush()
    return svc


def link_scan_service(db, scan_id: int, service_id: int) -> None:
    exists = (
        db.query(ScanService)
        .filter(
            ScanService.scan_id == scan_id,
            ScanService.service_id == service_id,
        )
        .one_or_none()
    )
    if not exists:
        db.add(ScanService(scan_id=scan_id, service_id=service_id))


# ─── Web endpoint helpers ──────────────────────────────────────────────────

def upsert_web_endpoint(
    db,
    asset_id: int,
    url: str,
    scheme: Optional[str],
    host: Optional[str],
    port: Optional[int],
    path: Optional[str],
    status_code: Optional[int],
    title: Optional[str],
    webserver: Optional[str],
) -> WebEndpoint:
    ep = (
        db.query(WebEndpoint)
        .filter(WebEndpoint.asset_id == asset_id, WebEndpoint.url == url)
        .one_or_none()
    )
    if ep:
        ep.status_code = status_code
        ep.title = title
        ep.webserver = webserver
        db.flush()
        return ep

    ep = WebEndpoint(
        asset_id=asset_id,
        url=url,
        scheme=scheme,
        host=host,
        port=port,
        path=path,
        status_code=status_code,
        title=title,
        webserver=webserver,
    )
    db.add(ep)
    db.flush()
    return ep


def link_scan_web_endpoint(db, scan_id: int, web_endpoint_id: int) -> None:
    exists = (
        db.query(ScanWebEndpoint)
        .filter(
            ScanWebEndpoint.scan_id == scan_id,
            ScanWebEndpoint.web_endpoint_id == web_endpoint_id,
        )
        .one_or_none()
    )
    if not exists:
        db.add(ScanWebEndpoint(scan_id=scan_id, web_endpoint_id=web_endpoint_id))


# ─── Risk scoring ──────────────────────────────────────────────────────────

_SEVERITY_BASE = {
    FindingSeverity.INFO.value: 10,
    FindingSeverity.LOW.value: 30,
    FindingSeverity.MEDIUM.value: 60,
    FindingSeverity.HIGH.value: 85,
    FindingSeverity.CRITICAL.value: 100,
}

_HIGH_RISK_PORTS = {23, 445, 3389}
_MEDIUM_RISK_PORTS = {21, 3306, 5432, 5900}


def severity_base_score(severity: str) -> int:
    return _SEVERITY_BASE.get(severity, 10)


def port_bonus(port: Optional[int]) -> int:
    if port is None:
        return 0
    if port in _HIGH_RISK_PORTS:
        return 10
    if port in _MEDIUM_RISK_PORTS:
        return 5
    return 0


def score_to_priority(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def calculate_risk_score(
    severity: str,
    port: Optional[int] = None,
    has_web: bool = False,
) -> tuple[int, str]:
    score = severity_base_score(severity) + port_bonus(port)
    if has_web:
        score += 5
    score = min(score, 100)
    return score, score_to_priority(score)


def service_severity(port: int) -> str:
    if port in _HIGH_RISK_PORTS:
        return FindingSeverity.HIGH.value
    if port in _MEDIUM_RISK_PORTS:
        return FindingSeverity.MEDIUM.value
    return FindingSeverity.INFO.value


# ─── Finding creation ──────────────────────────────────────────────────────

def create_finding(
    db,
    scan_id: int,
    title: str,
    severity: str,
    description: Optional[str] = None,
    confidence: str = "medium",
    evidence: Optional[str] = None,
    recommendation: Optional[str] = None,
    asset_id: Optional[int] = None,
    service_id: Optional[int] = None,
    web_endpoint_id: Optional[int] = None,
    port: Optional[int] = None,
    has_web: bool = False,
) -> Finding:
    risk_score, priority = calculate_risk_score(severity=severity, port=port, has_web=has_web)

    finding = Finding(
        scan_id=scan_id,
        asset_id=asset_id,
        service_id=service_id,
        web_endpoint_id=web_endpoint_id,
        title=title,
        severity=severity,
        description=description,
        confidence=confidence,
        evidence=evidence,
        recommendation=recommendation,
        risk_score=risk_score,
        priority=priority,
    )
    db.add(finding)
    db.flush()
    return finding
