"""
Container runner — single point of contact between RASID and DinD.
"""
from __future__ import annotations

import os
import time
from typing import Sequence

import docker  # type: ignore

from app.logging_setup import logger
from app.tools.registry import ToolSpec


class ContainerRunResult:
    __slots__ = ("exit_code", "stdout", "stderr", "raw_text")

    def __init__(self, exit_code: int, raw_text: str):
        self.exit_code = exit_code
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
    raw_args = list(args) if args is not None else list(spec.default_args)
    raw_args = _substitute_target(raw_args, target)
    logger.info("FINAL COMMAND %s", raw_args)

    if spec.target_position == "trailing" and target not in raw_args:
        raw_args.append(target)

    logger.info("Running tool %s with args=%s", spec.name, raw_args)

    client = _docker_client(spec.timeout_seconds)

    container_kwargs = {
        "image": spec.image,
        "command": raw_args,
        "detach": True,
        "tty": True,
        "dns": ["8.8.8.8", "1.1.1.1"],
    }

    if spec.name == "masscan":
        container_kwargs["cap_add"] = ["NET_ADMIN", "NET_RAW"]

    if stdin_data is not None:
        container_kwargs["stdin_open"] = True

    container = client.containers.run(**container_kwargs)
    logger.info("Container started: %s", container.id[:12])

    try:
        if stdin_data is not None:
            sock = container.attach_socket(params={"stdin": 1, "stream": 1})
            try:
                sock._sock.sendall(stdin_data.encode("utf-8"))  # type: ignore[attr-defined]
                sock._sock.shutdown(1)  # type: ignore[attr-defined]
            finally:
                sock.close()

        # Poll for container exit instead of long-running HTTP wait() which
        # hits the docker client's read timeout on long scans (amass, nuclei).
        start = time.time()
        while True:
            container.reload()
            if container.status in ("exited", "dead"):
                break
            if time.time() - start > spec.timeout_seconds:
                logger.warning("Container %s exceeded timeout, killing", container.id[:12])
                try:
                    container.kill()
                except Exception:  # noqa: BLE001
                    pass
                break
            time.sleep(3)

        container.reload()
        exit_code = container.attrs["State"]["ExitCode"]
        logger.info("Container %s exited with code %s", container.id[:12], exit_code)

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
