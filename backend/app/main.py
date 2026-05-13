"""
RASID Flask application factory.

This module is intentionally thin: it builds the Flask app, wires CORS,
rate limiting, error handlers and the blueprints in app.api. All route
logic lives in app.api.*.

Schema management is exclusively handled by Alembic — run
`alembic upgrade head` before starting the app.
"""
from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.api import ALL_BLUEPRINTS
from app.logging_setup import logger


def _build_cors_origins() -> list[str]:
    """Allow overriding allowed origins via env (CORS_ORIGINS, comma-separated).
    Defaults match the dev Vite ports for convenience.
    """
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,http://localhost:3000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def _configure_rate_limiter(app: Flask) -> None:
    """Apply Flask-Limiter when available. Optional: if the package is not
    installed the app still starts (with a warning) so test environments
    that don't need rate limiting aren't blocked.
    """
    try:
        from flask_limiter import Limiter  # type: ignore
        from flask_limiter.util import get_remote_address  # type: ignore
    except ImportError:
        logger.warning("flask-limiter not installed — rate limiting disabled")
        return

    storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],  # tighter limits applied per-route
        storage_uri=storage_uri,
    )

    # Login is a brute-force-prone endpoint.
    limiter.limit("10 per minute")(app.view_functions["auth.login"])
    # Registration is rarer; still capped to deter abuse.
    limiter.limit("5 per minute")(app.view_functions["auth.register"])
    # Scan creation: expensive in compute terms.
    limiter.limit("30 per hour")(app.view_functions["scans.create_scan"])
    # Password change & API key rotation are state-changing and infrequent.
    # An attacker who steals an API key but lacks the password should not
    # be able to spray attempts at change_password.
    for endpoint in ("settings.change_password", "settings.rotate_api_key",
                     "settings.delete_account"):
        if endpoint in app.view_functions:
            limiter.limit("10 per hour")(app.view_functions[endpoint])
    # Report downloads can be heavy when there are many findings.
    if "reports.download_report" in app.view_functions:
        limiter.limit("60 per hour")(app.view_functions["reports.download_report"])


def create_app() -> Flask:
    app = Flask(__name__)

    # Cap request bodies. Every endpoint here is JSON; 1 MiB is far above
    # anything legitimate (the biggest realistic payload is a custom tool
    # args list, ~32 short strings). Without this an attacker can ship
    # arbitrarily large JSON and force Flask to buffer it all.
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1 MiB

    CORS(
        app,
        resources={r"/api/*": {"origins": _build_cors_origins()}},
        allow_headers=["Content-Type", "X-API-Key"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    @app.errorhandler(Exception)
    def handle_exception(e):
        # HTTP errors keep their status; anything else returns generic 500.
        if isinstance(e, HTTPException):
            return jsonify({"ok": False, "error": e.description}), e.code
        logger.exception("Unhandled exception in request")
        return jsonify({"ok": False, "error": "internal server error"}), 500

    @app.errorhandler(404)
    def handle_not_found(_e):
        return jsonify({"ok": False, "error": "not found"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(_e):
        return jsonify({"ok": False, "error": "method not allowed"}), 405

    @app.errorhandler(429)
    def handle_rate_limit(_e):
        return jsonify({"ok": False, "error": "rate limit exceeded"}), 429

    @app.errorhandler(413)
    def handle_payload_too_large(_e):
        return jsonify({"ok": False, "error": "request body too large"}), 413

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "rasid-api"})

    # ── Register all blueprints ──────────────────────────────────────────
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    _configure_rate_limiter(app)

    logger.info("RASID API started — %d blueprints registered", len(ALL_BLUEPRINTS))
    return app


app = create_app()
