"""Report generation: JSON, HTML, Markdown."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape as _h

from flask import Blueprint, Response, g, jsonify, request

from app.auth import require_api_key
from app.audit import audit
from app.db import SessionLocal
from app.models import Finding, ScanJob, UserRole
from app.serializers import finding_to_dict


bp = Blueprint("reports", __name__, url_prefix="/api")


SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#16a34a",
    "info": "#6b7280",
}


def _scan_for_user(db, scan_id: int):
    uid = g.current_user["id"]
    is_admin = g.current_user["role"] == UserRole.ADMIN.value
    q = db.query(ScanJob).filter(ScanJob.id == scan_id)
    if not is_admin:
        q = q.filter(ScanJob.user_id == uid)
    return q.one_or_none()


def _build_html(job: ScanJob, findings) -> str:
    # Every finding field is escaped before interpolation. Scan tool output
    # (httpx titles, nuclei evidence, etc.) is untrusted — without escaping,
    # a target that returns `<script>...` in its HTML title would land
    # verbatim in this report and execute when the user opens it.
    rows: list[str] = []
    for f in findings:
        color = SEVERITY_COLORS.get(f.severity, "#6b7280")
        rows.append(f"""
        <tr>
            <td>{_h(f.title or '')}</td>
            <td><span style="color:{color};font-weight:bold">{_h((f.severity or '').upper())}</span></td>
            <td>{int(f.risk_score or 0)}</td>
            <td>{_h(f.confidence or '')}</td>
            <td>{_h(f.description or '')}</td>
            <td><code>{_h(f.evidence or '')}</code></td>
            <td>{_h(f.recommendation or '')}</td>
        </tr>""")
    body_rows = "".join(rows) if rows else \
        '<tr><td colspan="7" style="text-align:center;color:#64748b">No findings</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:;">
<title>RASID Report — {_h(job.target)}</title>
<style>
  body {{ font-family: Inter, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 24px; }}
  h1 {{ color: #14b8a6; }} h2 {{ color: #94a3b8; font-size: 14px; font-weight: 400; margin-top: 0; }}
  .meta {{ display: flex; gap: 24px; margin: 20px 0; flex-wrap: wrap; }}
  .meta span {{ background: #1e293b; padding: 8px 14px; border-radius: 8px; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
  th {{ background: #1e293b; padding: 10px 12px; text-align: left; font-size: 13px; color: #94a3b8; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #1e293b; font-size: 13px; vertical-align: top; }}
  code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #67e8f9; }}
</style>
</head>
<body>
<h1>🛡 RASID Security Report</h1>
<h2>Reconnaissance Automation System</h2>
<div class="meta">
  <span>Target: <b>{_h(job.target)}</b></span>
  <span>Tool: <b>{_h(job.tool)}</b></span>
  <span>Status: <b>{_h(job.status)}</b></span>
  <span>Findings: <b>{len(findings)}</b></span>
  <span>Generated: <b>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</b></span>
</div>
<table>
  <thead><tr>
    <th>Title</th><th>Severity</th><th>Risk</th>
    <th>Confidence</th><th>Description</th><th>Evidence</th><th>Recommendation</th>
  </tr></thead>
  <tbody>{body_rows}</tbody>
</table>
</body></html>"""


def _build_markdown(job: ScanJob, findings) -> str:
    lines = [
        f"# RASID Security Report — {job.target}",
        "",
        f"- **Tool**: `{job.tool}`",
        f"- **Status**: `{job.status}`",
        f"- **Findings**: **{len(findings)}**",
        f"- **Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("_No findings._")
    else:
        for f in findings:
            lines.extend([
                f"### {f.title}",
                "",
                f"- **Severity**: `{f.severity}` ({f.priority})",
                f"- **Risk score**: {f.risk_score}",
                f"- **Confidence**: {f.confidence}",
                "",
                f.description or "",
                "",
            ])
            if f.evidence:
                lines.extend(["**Evidence**:", "", "```", f.evidence, "```", ""])
            if f.recommendation:
                lines.extend([f"**Recommendation**: {f.recommendation}", ""])
            lines.append("---")
            lines.append("")
    return "\n".join(lines)


@bp.get("/scans/<int:scan_id>/report")
@require_api_key
def download_report(scan_id: int):
    fmt = request.args.get("format", "json").lower()
    if fmt not in ("json", "html", "md", "markdown"):
        return jsonify({"ok": False, "error": "format must be one of: json, html, md"}), 400

    db = SessionLocal()
    try:
        job = _scan_for_user(db, scan_id)
        if not job:
            return jsonify({"ok": False, "error": "scan not found"}), 404

        findings = (
            db.query(Finding)
            .filter(Finding.scan_id == job.id)
            .order_by(Finding.risk_score.desc())
            .all()
        )

        audit(db, user_id=g.current_user["id"], action="report.download",
              resource_type="scan", resource_id=str(job.id),
              extra={"format": fmt}, commit=True)

        if fmt == "html":
            return Response(
                _build_html(job, findings),
                mimetype="text/html",
                headers={
                    "Content-Disposition": f'attachment; filename="rasid_report_{scan_id}.html"',
                    "X-Content-Type-Options": "nosniff",
                },
            )

        if fmt in ("md", "markdown"):
            return Response(
                _build_markdown(job, findings),
                mimetype="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="rasid_report_{scan_id}.md"',
                    "X-Content-Type-Options": "nosniff",
                },
            )

        # JSON (default)
        report = {
            "rasid_report": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scan": {
                "id": job.id, "target": job.target,
                "tool": job.tool, "status": job.status,
                "created_at": str(job.created_at),
                "started_at": str(job.started_at),
                "finished_at": str(job.finished_at),
            },
            "summary": {
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == "critical"),
                "high": sum(1 for f in findings if f.severity == "high"),
                "medium": sum(1 for f in findings if f.severity == "medium"),
                "low": sum(1 for f in findings if f.severity == "low"),
                "info": sum(1 for f in findings if f.severity == "info"),
            },
            "findings": [finding_to_dict(f) for f in findings],
        }
        return Response(
            json.dumps(report, indent=2, default=str),
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="rasid_report_{scan_id}.json"',
                "X-Content-Type-Options": "nosniff",
            },
        )
    finally:
        db.close()
