"""API blueprints package.

Each module under app.api defines a Flask Blueprint covering one bounded
slice of the API. Register them all in app.main.create_app().
"""
from app.api.admin_routes import bp as admin_bp
from app.api.auth_routes import bp as auth_bp
from app.api.dashboard_routes import bp as dashboard_bp
from app.api.data_routes import bp as data_bp
from app.api.legal_routes import bp as legal_bp
from app.api.notification_routes import bp as notification_bp
from app.api.report_routes import bp as report_bp
from app.api.scan_routes import bp as scan_bp
from app.api.settings_routes import bp as settings_bp
from app.api.tool_command_routes import bp as tool_command_bp


ALL_BLUEPRINTS = (
    auth_bp,
    dashboard_bp,
    scan_bp,
    data_bp,
    report_bp,
    notification_bp,
    tool_command_bp,
    legal_bp,
    settings_bp,
    admin_bp,
)


__all__ = ["ALL_BLUEPRINTS"]
