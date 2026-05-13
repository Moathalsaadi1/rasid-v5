"""RASID tool integration package.

Layout:
  registry.py       — ToolSpec catalogue (one entry per supported tool)
  runner.py         — Docker-in-Docker execution wrapper
  persistence.py    — Asset/Service/Finding helpers shared by every task
  parsers/          — Per-tool output parsers (pure functions)
"""
from app.tools.registry import REGISTRY, ToolSpec, get_tool, all_tool_names, is_known_tool

__all__ = [
    "REGISTRY",
    "ToolSpec",
    "get_tool",
    "all_tool_names",
    "is_known_tool",
]
