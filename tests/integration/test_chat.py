"""Integration tests for chat routes."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest


class TestChatEndpoint:
    def _register_and_get_token(self, client) -> str:
        res = client.post("/api/auth/register", json={
            "email": "chat@test.com",
            "password": "pass123",
        })
        return res.json()["access_token"]

    def test_chat_no_auth(self, client):
        res = client.post("/api/chat", json={"message": "Hallo"})
        assert res.status_code == 401

    @patch("gridbert.api.routes.chat.GridbertAgent")
    @patch("gridbert.api.routes.chat.build_default_registry")
    @patch("gridbert.api.routes.chat.ANTHROPIC_API_KEY", "sk-test")
    def test_chat_streams_events(self, mock_registry, mock_agent_class, client):
        token = self._register_and_get_token(client)

        # Mock agent
        from gridbert.agent.types import AgentEvent, EventType

        mock_agent = MagicMock()

        def fake_run(user_message, conversation_history, on_event, attachments=None):
            on_event(AgentEvent(type=EventType.TEXT_DELTA, data={"text": "Hallo!"}))
            on_event(AgentEvent(type=EventType.DONE, data={"final_text": "Hallo!"}))
            return "Hallo!"

        mock_agent.run.side_effect = fake_run
        mock_agent_class.return_value = mock_agent

        res = client.post(
            "/api/chat",
            json={"message": "Hi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")

        # Parse SSE events
        body = res.text
        events = []
        for line in body.split("\n\n"):
            line = line.strip()
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass

        # Should have text_delta, done, and final done with conversation_id
        types = [e["type"] for e in events]
        assert "text_delta" in types
        assert "done" in types

    @patch("gridbert.api.routes.chat.ANTHROPIC_API_KEY", "")
    def test_chat_no_api_key(self, client):
        token = self._register_and_get_token(client)
        res = client.post(
            "/api/chat",
            json={"message": "Hi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 503


class TestHistoryConversion:
    def test_converts_user_and_assistant(self):
        from gridbert.api.routes.chat import _history_to_messages

        history = [
            {"role": "user", "content": "Hallo"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "Wie geht's?"},
        ]
        result = _history_to_messages(history)
        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Hallo"}
        assert result[1] == {"role": "assistant", "content": "Hi!"}

    def test_skips_non_user_assistant(self):
        from gridbert.api.routes.chat import _history_to_messages

        history = [
            {"role": "user", "content": "Test"},
            {"role": "tool_result", "content": "..."},
            {"role": "assistant", "content": "Done"},
        ]
        result = _history_to_messages(history)
        assert len(result) == 2

    def test_empty_history(self):
        from gridbert.api.routes.chat import _history_to_messages

        assert _history_to_messages([]) == []


class TestConversations:
    def _register_and_chat(self, client):
        """Register, then simulate a conversation by directly inserting data."""
        res = client.post("/api/auth/register", json={
            "email": "conv@test.com",
            "password": "pass123",
        })
        return res.json()["access_token"]

    def test_list_conversations_empty(self, client):
        token = self._register_and_chat(client)
        res = client.get(
            "/api/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        assert res.json() == []
