"""Custom tool command endpoints (Phase 3, FR-12).

Lets registered users save a customized argument list per tool, which the
Celery task will use instead of the tool's default_args. All args pass
through the registry whitelist before they're allowed near a container.
"""
from __future__ import annotations

import json

from flask import Blueprint, g, jsonify, request

from app.audit import audit
from app.auth import get_json_body, require_api_key
from app.db import SessionLocal
from app.models import UserToolCommand
from app.serializers import tool_command_to_dict
from app.tool_args_validator import ArgsValidationError, validate_args
from app.tools.registry import REGISTRY, get_tool, is_known_tool


bp = Blueprint("tool_commands", __name__, url_prefix="/api")


@bp.get("/tools")
@require_api_key
def list_tools():
    """Expose the tool registry to the frontend (read-only).

    The UI uses this to build the tool picker and to show the user which
    flags they're allowed to use when authoring a custom command.
    """
    tools = []
    for name, spec in REGISTRY.items():
        tools.append({
            "name": spec.name,
            "description": spec.description,
            "default_args": list(spec.default_args),
            "allowed_flags": sorted(spec.allowed_flags),
            "target_position": spec.target_position,
            "timeout_seconds": spec.timeout_seconds,
        })
    return jsonify({"ok": True, "tools": tools})


@bp.get("/tools/commands")
@require_api_key
def list_commands():
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        rows = (
            db.query(UserToolCommand)
            .filter(UserToolCommand.user_id == uid)
            .order_by(UserToolCommand.tool_name)
            .all()
        )
        return jsonify({
            "ok": True,
            "commands": [tool_command_to_dict(r) for r in rows],
        })
    finally:
        db.close()


@bp.post("/tools/commands")
@require_api_key
def upsert_command():
    """Create or replace the custom command for one (user, tool) pair.

    Body: {"tool_name": "...", "name": "...", "args": ["-T4", "-F", ...]}
    """
    data = get_json_body()
    tool_name = (data.get("tool_name") or "").strip().lower()
    args = data.get("args")
    name = (data.get("name") or "custom").strip()[:120]

    if not is_known_tool(tool_name):
        return jsonify({"ok": False, "error": f"unknown tool: {tool_name}"}), 400

    if not isinstance(args, list):
        return jsonify({"ok": False, "error": "args must be a list of strings"}), 400

    try:
        cleaned = validate_args(tool_name, args)
    except ArgsValidationError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        existing = (
            db.query(UserToolCommand)
            .filter(
                UserToolCommand.user_id == uid,
                UserToolCommand.tool_name == tool_name,
            )
            .one_or_none()
        )

        args_json = json.dumps(cleaned)
        if existing:
            existing.args = args_json
            existing.name = name
            existing.is_active = True
            row = existing
            action = "tool_command.update"
        else:
            row = UserToolCommand(
                user_id=uid,
                tool_name=tool_name,
                name=name,
                args=args_json,
                is_active=True,
            )
            db.add(row)
            db.flush()
            action = "tool_command.create"

        audit(db, user_id=uid, action=action,
              resource_type="tool_command", resource_id=str(row.id),
              extra={"tool_name": tool_name})
        db.commit()
        db.refresh(row)

        return jsonify({"ok": True, "command": tool_command_to_dict(row)})
    finally:
        db.close()


@bp.delete("/tools/commands/<int:cid>")
@require_api_key
def delete_command(cid: int):
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        row = (
            db.query(UserToolCommand)
            .filter(UserToolCommand.id == cid, UserToolCommand.user_id == uid)
            .one_or_none()
        )
        if not row:
            return jsonify({"ok": False, "error": "command not found"}), 404

        audit(db, user_id=uid, action="tool_command.delete",
              resource_type="tool_command", resource_id=str(row.id))
        db.delete(row)
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@bp.post("/tools/commands/<int:cid>/toggle")
@require_api_key
def toggle_command(cid: int):
    """Enable or disable a saved command without deleting it."""
    db = SessionLocal()
    try:
        uid = g.current_user["id"]
        row = (
            db.query(UserToolCommand)
            .filter(UserToolCommand.id == cid, UserToolCommand.user_id == uid)
            .one_or_none()
        )
        if not row:
            return jsonify({"ok": False, "error": "command not found"}), 404

        row.is_active = not row.is_active
        audit(db, user_id=uid, action="tool_command.toggle",
              resource_type="tool_command", resource_id=str(row.id),
              extra={"is_active": row.is_active})
        db.commit()

        return jsonify({"ok": True, "command": tool_command_to_dict(row)})
    finally:
        db.close()
