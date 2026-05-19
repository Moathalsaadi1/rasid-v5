import enum
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AssetType(str, enum.Enum):
    DOMAIN = "DOMAIN"
    IP = "IP"
    URL = "URL"


class FindingSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    api_key = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default=UserRole.USER.value)
    is_active = Column(Boolean, nullable=False, default=True)
    scan_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scans = relationship("ScanJob", back_populates="user")


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    target = Column(String(255), nullable=False)
    tool = Column(String(50), nullable=False, default="nmap")
    status = Column(String(20), nullable=False, default=ScanStatus.PENDING.value)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="scans")
    assets = relationship("ScanAsset", back_populates="scan", cascade="all, delete-orphan")
    services = relationship("ScanService", back_populates="scan", cascade="all, delete-orphan")
    web_endpoints = relationship("ScanWebEndpoint", back_populates="scan", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)
    value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("type", "value", name="uq_asset_type_value"),
    )


class ScanAsset(Base):
    __tablename__ = "scan_assets"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(30), nullable=False, default="TARGET")

    scan = relationship("ScanJob", back_populates="assets")
    asset = relationship("Asset")

    __table_args__ = (
        UniqueConstraint("scan_id", "asset_id", "role", name="uq_scan_asset_role"),
    )


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    ip_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(10), nullable=False)
    state = Column(String(20), nullable=False)
    name = Column(String(80), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ip_asset = relationship("Asset")

    __table_args__ = (
        UniqueConstraint("ip_asset_id", "port", "protocol", name="uq_service_ip_port_proto"),
    )


class ScanService(Base):
    __tablename__ = "scan_services"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)

    scan = relationship("ScanJob", back_populates="services")
    service = relationship("Service")

    __table_args__ = (
        UniqueConstraint("scan_id", "service_id", name="uq_scan_service"),
    )


class WebEndpoint(Base):
    __tablename__ = "web_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)
    scheme = Column(String(20), nullable=True)
    host = Column(String(255), nullable=True)
    port = Column(Integer, nullable=True)
    path = Column(String(255), nullable=True)
    status_code = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    webserver = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    asset = relationship("Asset")

    __table_args__ = (
        UniqueConstraint("asset_id", "url", name="uq_web_endpoint_asset_url"),
    )


class ScanWebEndpoint(Base):
    __tablename__ = "scan_web_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    web_endpoint_id = Column(Integer, ForeignKey("web_endpoints.id", ondelete="CASCADE"), nullable=False)

    scan = relationship("ScanJob", back_populates="web_endpoints")
    web_endpoint = relationship("WebEndpoint")

    __table_args__ = (
        UniqueConstraint("scan_id", "web_endpoint_id", name="uq_scan_web_endpoint"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    web_endpoint_id = Column(Integer, ForeignKey("web_endpoints.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default=FindingSeverity.INFO.value)
    confidence = Column(String(20), nullable=False, default="medium")
    evidence = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    risk_score = Column(Integer, nullable=False, default=0)
    priority = Column(String(20), nullable=False, default="low")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan = relationship("ScanJob", back_populates="findings")
    asset = relationship("Asset")
    service = relationship("Service")
    web_endpoint = relationship("WebEndpoint")


# ─── Phase 3: Custom tool commands ─────────────────────────────────────────

class UserToolCommand(Base):
    """A user-saved customisation of a tool's command-line arguments.

    `args` is a JSON array of strings. When a scan is created and the user
    has a row here for the chosen tool, that array is used instead of the
    tool's default_args (after passing through the registry's allowed_flags
    whitelist for safety).
    """
    __tablename__ = "user_tool_commands"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(50), nullable=False)
    name = Column(String(120), nullable=False, default="custom")
    args = Column(Text, nullable=False)  # JSON-encoded list[str]
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "tool_name", name="uq_user_tool_command"),
    )


# ─── Phase 4: Notifications & audit logging ────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=True)
    severity = Column(String(20), nullable=False, default="medium")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    """Append-only log of every privileged or state-changing action.

    Captures who did what, on which resource, and from where. We deliberately
    keep this lean — high-volume audit storage belongs in a dedicated system.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(80), nullable=True)
    resource_id = Column(String(80), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    extra = Column(Text, nullable=True)  # free-form JSON, optional
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


# ─── Phase 5: Legal/Ethical acceptance ─────────────────────────────────────

class LegalAcceptance(Base):
    """Records that a user has accepted the platform's legal/ethical terms.

    Required before the user can create their first scan. Tracking version
    means we can require re-acceptance when the terms change.
    """
    __tablename__ = "legal_acceptances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    terms_version = Column(String(20), nullable=False)
    accepted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(64), nullable=True)
# ─── Aggregation Layer ──────────────────────────────────────────────────────

class AggregatedResult(Base):
    """Deduplicated cross-tool finding with source attribution.
    
    Updated automatically after every scan completes.
    One row per unique (target, category, value) combination.
    """
    __tablename__ = "aggregated_results"

    id         = Column(Integer, primary_key=True, index=True)
    target     = Column(String(255), nullable=False, index=True)
    category   = Column(String(30),  nullable=False)
    # subdomain | port | http_endpoint | vulnerability

    value      = Column(String(500), nullable=False)
    # sub.example.com | 443/tcp | https://... | CVE-2021-XXXX

    sources    = Column(Text, nullable=False, default="[]")
    # JSON: ["subfinder", "amass"]

    confidence = Column(String(10), nullable=False, default="low")
    # low=1 source, medium=2, high=3+

    meta       = Column(Text, nullable=True)
    # JSON: IPs, service name, severity, etc.

    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("target", "category", "value",
                         name="uq_aggregated_target_category_value"),
    )
