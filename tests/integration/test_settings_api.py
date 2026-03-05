"""Integration tests for settings routes — LLM API key management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gridbert.api.deps import get_db
from gridbert.api.routes.auth import router as auth_router
from gridbert.api.routes.settings import router as settings_router


@pytest.fixture()
def settings_app(db_engine):
    """FastAPI test app with settings + auth routers."""
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(settings_router, prefix="/api/settings")

    def _test_db():
        with db_engine.connect() as conn:
            yield conn
            conn.commit()

    app.dependency_overrides[get_db] = _test_db
    return app


@pytest.fixture()
def settings_client(settings_app) -> TestClient:
    return TestClient(settings_app)


@pytest.fixture()
def authed_settings_client(settings_client, auth_token) -> TestClient:
    settings_client.headers["Authorization"] = f"Bearer {auth_token}"
    return settings_client


class TestSetupStatus:
    def test_unauthenticated(self, settings_client):
        res = settings_client.get("/api/settings/status")
        assert res.status_code == 401

    @patch("gridbert.api.routes.settings.ANTHROPIC_API_KEY", "")
    def test_needs_setup_no_keys(self, authed_settings_client):
        res = authed_settings_client.get("/api/settings/status")
        assert res.status_code == 200
        data = res.json()
        assert data["needs_setup"] is True
        assert data["has_user_key"] is False
        assert data["has_server_key"] is False

    @patch("gridbert.api.routes.settings.ANTHROPIC_API_KEY", "sk-server-key")
    def test_has_server_key(self, authed_settings_client):
        res = authed_settings_client.get("/api/settings/status")
        data = res.json()
        assert data["has_server_key"] is True
        assert data["needs_setup"] is False


class TestGetLLMConfig:
    def test_no_config(self, authed_settings_client):
        res = authed_settings_client.get("/api/settings/llm")
        data = res.json()
        assert data["has_key"] is False
        assert data["provider"] == ""
        assert data["model"] == ""


class TestSetLLMConfig:
    def test_invalid_provider(self, authed_settings_client):
        res = authed_settings_client.put("/api/settings/llm", json={
            "provider": "invalid",
            "api_key": "sk-test",
        })
        assert res.status_code == 400

    def test_empty_key(self, authed_settings_client):
        res = authed_settings_client.put("/api/settings/llm", json={
            "provider": "claude",
            "api_key": "",
        })
        assert res.status_code == 400

    @patch("gridbert.api.routes.settings.create_provider")
    def test_valid_key_stored(self, mock_create, authed_settings_client):
        """Mock the provider validation and verify key is encrypted."""
        mock_provider = MagicMock()
        mock_create.return_value = mock_provider

        res = authed_settings_client.put("/api/settings/llm", json={
            "provider": "claude",
            "api_key": "sk-ant-test-key-123",
            "model": "claude-haiku-4-5-20251001",
        })
        assert res.status_code == 200
        data = res.json()
        assert data["has_key"] is True
        assert data["provider"] == "claude"
        assert data["model"] == "claude-haiku-4-5-20251001"

        # Verify it's persisted
        res2 = authed_settings_client.get("/api/settings/llm")
        assert res2.json()["has_key"] is True
        assert res2.json()["provider"] == "claude"

    @patch("gridbert.api.routes.settings.create_provider")
    def test_key_validation_failure(self, mock_create, authed_settings_client):
        mock_provider = MagicMock()
        mock_provider.chat.side_effect = Exception("Invalid API key")
        mock_create.return_value = mock_provider

        res = authed_settings_client.put("/api/settings/llm", json={
            "provider": "openai",
            "api_key": "sk-invalid",
        })
        assert res.status_code == 400
        assert "ungültig" in res.json()["detail"]


class TestDeleteLLMConfig:
    @patch("gridbert.api.routes.settings.create_provider")
    def test_delete_config(self, mock_create, authed_settings_client):
        mock_create.return_value = MagicMock()

        # First set a config
        authed_settings_client.put("/api/settings/llm", json={
            "provider": "claude",
            "api_key": "sk-test",
            "model": "claude-haiku-4-5-20251001",
        })

        # Delete it
        res = authed_settings_client.delete("/api/settings/llm")
        assert res.status_code == 200
        assert res.json()["status"] == "removed"

        # Verify it's gone
        res2 = authed_settings_client.get("/api/settings/llm")
        assert res2.json()["has_key"] is False
