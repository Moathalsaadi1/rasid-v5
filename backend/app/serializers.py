"""Shared dict serializers for ORM objects."""
from __future__ import annotations


def job_to_dict(job) -> dict:
    return {
        "id": job.id,
        "target": job.target,
        "tool": job.tool,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error_message": job.error_message,
    }


def finding_to_dict(f) -> dict:
    return {
        "id": f.id,
        "title": f.title,
        "severity": f.severity,
        "priority": f.priority,
        "risk_score": f.risk_score,
        "confidence": f.confidence,
        "description": f.description,
        "evidence": f.evidence,
        "recommendation": f.recommendation,
        "asset_id": f.asset_id,
        "service_id": f.service_id,
        "web_endpoint_id": f.web_endpoint_id,
        "created_at": f.created_at,
    }


def notification_to_dict(n) -> dict:
    return {
        "id": n.id,
        "scan_id": n.scan_id,
        "severity": n.severity,
        "title": n.title,
        "message": n.message,
        "is_read": n.is_read,
        "created_at": n.created_at,
    }


def audit_to_dict(a) -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "action": a.action,
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "ip_address": a.ip_address,
        "created_at": a.created_at,
    }


def tool_command_to_dict(tc) -> dict:
    import json
    try:
        args = json.loads(tc.args) if tc.args else []
    except (json.JSONDecodeError, ValueError):
        args = []
    return {
        "id": tc.id,
        "tool_name": tc.tool_name,
        "name": tc.name,
        "args": args,
        "is_active": tc.is_active,
        "created_at": tc.created_at,
        "updated_at": tc.updated_at,
    }
