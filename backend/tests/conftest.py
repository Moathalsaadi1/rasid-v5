"""
pytest fixtures for RASID.

Strategy: use SQLite in-memory + Celery EAGER mode so tests run without
needing real Postgres, Redis, or DinD. The Docker runner is monkey-patched
in individual tests where needed; here we just bring up the schema and
a Flask test client.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the backend/ directory is on PYTHONPATH so `import app.*` works
# regardless of where pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Force test-friendly env BEFORE importing the app.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_BROKER_URL", "memory://")
os.environ.setdefault("REDIS_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("ALLOW_PRIVATE_TARGETS", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")
# Critical: prevent the rate limiter from blocking tests.
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# A single in-memory SQLite engine shared across all DB sessions during a
# test run. StaticPool keeps the same connection alive so multiple sessions
# see the same data (without it each session gets a fresh empty DB).
_TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


@pytest.fixture(scope="session", autouse=True)
def _patch_db_module():
    """Replace app.db.engine and app.db.SessionLocal with the test ones.

    Done at session scope so the patch survives across tests.
    """
    from app import db as db_module

    db_module.engine = _TEST_ENGINE
    db_module.SessionLocal = _TestSessionLocal

    # Create all tables from the SQLAlchemy metadata (we don't run Alembic
    # in tests because some PostgreSQL-only constructs aren't valid in
    # SQLite — the ORM models are portable, so create_all is fine here).
    from app.models import Base
    Base.metadata.create_all(bind=_TEST_ENGINE)

    yield


@pytest.fixture(autouse=True)
def _reset_db():
    """Wipe data between tests so they're independent. Schema is preserved."""
    yield
    from app.models import Base
    with _TEST_ENGINE.begin() as conn:
        # Delete in FK-safe order (children first). SQLAlchemy's
        # metadata.sorted_tables already gives parent-first; reverse it.
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f"DELETE FROM {table.name}")


@pytest.fixture
def app():
    """Flask app with eager Celery (no real worker needed)."""
    # Eager Celery: tasks execute synchronously in the same process.
    from app.celery_app import celery
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True

    from app.main import create_app
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Helper: create a user without hitting /register (faster) ──────────────

@pytest.fixture
def db_session():
    """Direct DB access for fixtures that need to seed data."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_user(db, email: str, password: str, role: str = "user", accept_terms: bool = True):
    """Test helper: create a user with optional pre-accepted ToS."""
    from app.legal import CURRENT_TERMS_VERSION
    from app.models import LegalAcceptance, User
    from app.security import hash_password
    import secrets

    user = User(
        email=email,
        password_hash=hash_password(password),
        api_key="test_" + secrets.token_urlsafe(16),
        role=role,
    )
    db.add(user)
    db.flush()

    if accept_terms:
        db.add(LegalAcceptance(user_id=user.id, terms_version=CURRENT_TERMS_VERSION))

    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def make_user(db_session):
    """Factory fixture — call `make_user(email, password, ...)`."""
    def _factory(email: str, password: str = "password12345", role: str = "user",
                 accept_terms: bool = True):
        return _make_user(db_session, email, password, role, accept_terms)
    return _factory
