"""
Centralized logging configuration for the RASID backend.

All modules should import `logger` from here instead of using `print()`
or per-module loggers, to ensure consistent log formatting and routing.
"""
import logging
import os
import sys


def _build_logger() -> logging.Logger:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    log = logging.getLogger("rasid")
    log.setLevel(log_level)
    log.propagate = False

    if log.handlers:
        return log

    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    log.addHandler(handler)

    return log


logger = _build_logger()
