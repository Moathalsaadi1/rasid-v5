"""
Tool registry — a central catalogue of every reconnaissance tool RASID
can execute, together with the metadata the rest of the application
needs about it (image, default args, allowed flags, parser).

Adding a new tool: append a ToolSpec entry here and register a parser
in app.tools.parsers. No other file should need changes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class ToolSpec:
    name: str
    image: str
    description: str
    default_args: tuple[str, ...]
    # Flags allowed when a user provides custom command args. Anything not in
    # this list will be rejected by the validator. Conservative on purpose.
    allowed_flags: frozenset[str]
    # Whether the target is appended at the end of the command (typical) or
    # passed via a specific flag.
    target_position: str = "trailing"  # "trailing" or "via:<flag>"
    # Default per-scan timeout (seconds). Override per-tool because nuclei,
    # masscan and amass can legitimately need much longer than nmap.
    timeout_seconds: int = 300
    # Some tools accept stdin as an alternative input channel; not used yet.
    accepts_stdin: bool = False


def _img(env_key: str, default: str) -> str:
    return os.getenv(env_key, default)


# ─── Registry ──────────────────────────────────────────────────────────────

REGISTRY: dict[str, ToolSpec] = {
    "nmap": ToolSpec(
        name="nmap",
        image=_img("TOOL_NMAP_IMAGE", "instrumentisto/nmap:latest"),
        description="Network port and service scanner",
        default_args=("-T3", "-F", "-oX", "-"),
        allowed_flags=frozenset({
            "-T0", "-T1", "-T2", "-T3", "-T4",  # timing templates (T5 omitted on purpose)
            "-F",                                # fast (top-100 ports)
            "-sV",                               # service version detection
            "-sC",                               # default script scan
            "-Pn",                               # skip host discovery
            "-O",                                # OS detection
            "--top-ports",                       # top-N ports
            "-p",                                # specific ports
            "-oX",                               # XML output (always required)
        }),
        timeout_seconds=1800,
    ),

    "httpx": ToolSpec(
        name="httpx",
        image=_img("TOOL_HTTPX_IMAGE", "projectdiscovery/httpx:latest"),
        description="HTTP probing and web endpoint discovery",
        default_args=(
            "-u", "{TARGET}",
            "-json", "-silent",
            "-status-code", "-title", "-web-server",
        ),
        allowed_flags=frozenset({
            "-u", "-json", "-silent", "-status-code", "-title",
            "-web-server", "-tech-detect", "-follow-redirects",
            "-no-color", "-timeout", "-retries", "-rate-limit",
            "-mc", "-fc",
        }),
        target_position="via:-u",
        timeout_seconds=300,
    ),

    "nuclei": ToolSpec(
        name="nuclei",
        image=_img("TOOL_NUCLEI_IMAGE", "projectdiscovery/nuclei:latest"),
        description="Template-based vulnerability scanner",
     default_args=(
    "-u", "{TARGET}",
    "-jsonl", "-omit-raw",
    "-tags", "kev,cve",                         
    "-severity", "medium,high,critical",
    "-rl", "25", "-c", "5",
    "-timeout", "5", "-retries", "1",
    "-duc",
    ),
        allowed_flags=frozenset({
            "-u", "-jsonl", "-omit-raw", "-severity", "-rl", "-c",
            "-timeout", "-retries", "-duc", "-tags", "-exclude-tags",
            "-templates", "-no-color",
        }),
        target_position="via:-u",
        timeout_seconds=1800,
    ),

    "subfinder": ToolSpec(
        name="subfinder",
        image=_img("TOOL_SUBFINDER_IMAGE", "projectdiscovery/subfinder:latest"),
        description="Passive subdomain enumeration",
        default_args=("-d", "{TARGET}", "-silent", "-oJ"),
        allowed_flags=frozenset({
            "-d", "-silent", "-oJ", "-all", "-recursive",
            "-timeout", "-no-color", "-rl",
        }),
        target_position="via:-d",
        timeout_seconds=300,
    ),

   "amass": ToolSpec(
    name="amass",
    image=_img("TOOL_AMASS_IMAGE", "caffix/amass:latest"),
    description="Active and passive subdomain enumeration",
    default_args=(
        "enum", "-passive",
        "-d", "{TARGET}",
        "-nocolor",
        "-timeout", "5",        # حد أقصى 5 دقائق
        "-norecursive",         # ما يعمل recursive brute force
    ),
    allowed_flags=frozenset({
        "enum", "intel", "-d", "-passive", "-active",
        "-timeout", "-nocolor", "-norecursive",
    }),
    target_position="via:-d",
    timeout_seconds=1800,       # 30 دقيقة كحد أقصى للـ container
    ),

    "masscan": ToolSpec(
        name="masscan",
        image=_img("TOOL_MASSCAN_IMAGE", "secsi/masscan:latest"),
        description="Fast port scanner (large ranges)",
        # Conservative defaults: top common ports, low rate. The user can
        # only tune within the allowed_flags whitelist.
        default_args=(
            "-p", "21,22,23,25,53,80,110,139,143,443,445,993,995,1433,3306,3389,5432,5900,6379,8080,8443,11211,27017",
            "--rate", "1000",
            "--wait", "0",
            "-oJ", "-",
            "{TARGET}",
        ),
        allowed_flags=frozenset({
            "-p", "--ports", "--rate", "--wait", "-oJ", "-oX",
            "--top-ports", "--banners", "--open-only",
        }),
        timeout_seconds=1800,
    ),

    "massdns": ToolSpec(
        name="massdns",
        image=_img("TOOL_MASSDNS_IMAGE", "rasid/massdns:latest"),
        description="High-performance DNS resolver",
        # massdns reads a wordlist from stdin in real workflows; here we
        # invoke it on a single target to validate connectivity / record
        # presence. A bigger pipeline (subfinder → massdns) is the typical
        # production use, which is left as a future enhancement.
        default_args=(
            "{TARGET}",
            "-r", "/etc/massdns/resolvers.txt",
            "-t", "A",
            "-o", "J",
            "-q",
        ),
        allowed_flags=frozenset({
            "-r", "-t", "-o", "-q", "-c", "-s", "--retry",
        }),
        accepts_stdin=False,
        target_position="via:{TARGET}",
        timeout_seconds=300,
    ),
}


def get_tool(name: str) -> Optional[ToolSpec]:
    return REGISTRY.get(name)


def all_tool_names() -> list[str]:
    return list(REGISTRY.keys())


def is_known_tool(name: str) -> bool:
    return name in REGISTRY
    
  
