"""
Container runner — single point of contact between RASID and DinD.

Every tool task in app.tools.* funnels its execution through `run_tool()`,
which:
  * pulls the right image based on the ToolSpec
  * substitutes {TARGET} placeholders in args
  * spawns a detached container with safe defaults (DNS, network, removal)
  * waits with timeout, captures combined stdout+stderr
  * always cleans up the container even on failure

The runner does NOT decide what the args mean — that is the parser's job.
"""
from __future__ import annotations

import os
from typing import Sequence

import docker  # type: ignore

from app.logging_setup import logger
from app.tools.registry import ToolSpec


class ContainerRunResult:
    __slots__ = ("exit_code", "stdout", "stderr", "raw_text")

    def __init__(self, exit_code: int, raw_text: str):
        self.exit_code = exit_code
        # Docker SDK does not separate stdout/stderr by default when
        # container.logs() is called without streams; we keep them merged
        # in raw_text and expose stdout==raw_text, stderr=="" so callers
        # who care only about output keep working.
        self.stdout = raw_text
        self.stderr = ""
        self.raw_text = raw_text


def _docker_client(timeout: int) -> docker.DockerClient:
    return docker.DockerClient(
        base_url=os.getenv("DOCKER_HOST", "tcp://docker:2375"),
        timeout=timeout + 60,
    )


def _substitute_target(args: Sequence[str], target: str) -> list[str]:
    return [a.replace("{TARGET}", target) if isinstance(a, str) else a for a in args]


def run_tool(
    spec: ToolSpec,
    target: str,
    args: Sequence[str] | None = None,
    stdin_data: str | None = None,
) -> ContainerRunResult:
    """
    Execute the given tool on the given target.

    Args:
        spec: ToolSpec from the registry.
        target: validated target string (must already be safe).
        args: full argument list. If None, spec.default_args is used.
              {TARGET} placeholders are substituted with the target.
              For tools with target_position == "trailing", target is
              also appended at the end if not already present.
        stdin_data: optional string to feed via stdin (used for massdns).

    Returns:
        ContainerRunResult with exit_code and raw output.
    """
    raw_args = list(args) if args is not None else list(spec.default_args)
    raw_args = _substitute_target(raw_args, target)

    if spec.target_position == "trailing" and target not in raw_args:
        raw_args.append(target)

    logger.info("Running tool %s with args=%s", spec.name, raw_args)

    client = _docker_client(spec.timeout_seconds)

    container_kwargs = {
        "image": spec.image,
        "command": raw_args,
        "detach": True,
        "dns": ["8.8.8.8", "1.1.1.1"],
    }

    # masscan needs raw socket capability; without it the scan silently
    # produces no output.
    if spec.name == "masscan":
        container_kwargs["cap_add"] = ["NET_ADMIN", "NET_RAW"]

    if stdin_data is not None:
        container_kwargs["stdin_open"] = True

    container = client.containers.run(**container_kwargs)

    try:
        if stdin_data is not None:
            sock = container.attach_socket(params={"stdin": 1, "stream": 1})
            try:
                sock._sock.sendall(stdin_data.encode("utf-8"))  # type: ignore[attr-defined]
                sock._sock.shutdown(1)  # type: ignore[attr-defined]
            finally:
                sock.close()

        result = container.wait(timeout=spec.timeout_seconds)
        exit_code = int(result.get("StatusCode", 1))

        raw_logs = container.logs(stdout=True, stderr=True)
        raw_text = raw_logs.decode("utf-8", errors="replace")
    finally:
        try:
            container.remove(force=True)
        except Exception:  # noqa: BLE001
            logger.debug("Failed to remove container %s", container.id)

    logger.info("Tool %s finished exit_code=%s output_len=%s",
                spec.name, exit_code, len(raw_text))

    return ContainerRunResult(exit_code, raw_text)
