"""Shared fixtures for Gridbert tests."""

from __future__ import annotations

import os

# Force test config BEFORE any gridbert imports
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import Connection, create_engine, event
from sqlalchemy.pool import StaticPool

from gridbert.storage.schema import metadata


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    """Reset in-memory rate limiter between tests."""
    from gridbert.api.rate_limit import _requests

    _requests.clear()


@pytest.fixture()
def db_engine():
    """In-memory SQLite engine with shared connection pool.

    StaticPool ensures all connections share the same underlying SQLite
    database, which is required for in-memory SQLite.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_conn(db_engine) -> Connection:
    """DB connection for a single test — auto-commits on exit."""
    with db_engine.connect() as conn:
        yield conn
        conn.commit()


@pytest.fixture()
def test_user(db_conn) -> dict:
    """Create a test user and return their data."""
    import bcrypt

    from gridbert.storage.repositories.user_repo import create_user, get_user_by_id

    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
    user_id = create_user(db_conn, email="test@example.com", password_hash=pw_hash, name="Test User")
    db_conn.commit()
    return get_user_by_id(db_conn, user_id)


@pytest.fixture()
def auth_token(test_user) -> str:
    """JWT token for the test user."""
    from gridbert.api.routes.auth import _create_token

    return _create_token(test_user["id"])


@pytest.fixture()
def app(db_engine):
    """FastAPI test app with in-memory DB."""
    from fastapi import FastAPI

    from gridbert.api.routes.auth import router as auth_router
    from gridbert.api.routes.chat import router as chat_router
    from gridbert.api.routes.dashboard import router as dashboard_router

    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api/auth")
    test_app.include_router(chat_router, prefix="/api")
    test_app.include_router(dashboard_router, prefix="/api/dashboard")

    # Override DB dependency to use test engine
    from gridbert.api.deps import get_db

    def _test_db():
        with db_engine.connect() as conn:
            yield conn
            conn.commit()

    test_app.dependency_overrides[get_db] = _test_db

    return test_app


@pytest.fixture()
def client(app) -> "TestClient":
    """FastAPI TestClient."""
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture()
def authed_client(client, auth_token) -> "TestClient":
    """TestClient with auth header set."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client
