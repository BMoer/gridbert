"""Tests for LLM provider abstraction — Claude & OpenAI content building, response normalization."""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from gridbert.llm.types import LLMResponse, LLMTextBlock, LLMToolUseBlock


# ──────────────────────────────────────────────
# Claude Provider
# ──────────────────────────────────────────────


class TestClaudeProviderContentBuilding:
    def _provider(self):
        with patch("anthropic.Anthropic"):
            from gridbert.llm.claude_provider import ClaudeProvider
            return ClaudeProvider(api_key="test", model="claude-test")

    def test_plain_text(self):
        p = self._provider()
        assert p.build_user_content("Hallo") == "Hallo"

    def test_empty_attachments(self):
        p = self._provider()
        assert p.build_user_content("Hallo", []) == "Hallo"

    def test_pdf_attachment(self):
        p = self._provider()
        data = base64.b64encode(b"fake-pdf").decode()
        result = p.build_user_content("Analysiere", [
            {"media_type": "application/pdf", "data": data},
        ])
        assert isinstance(result, list)
        doc_blocks = [b for b in result if b.get("type") == "document"]
        assert len(doc_blocks) == 1
        assert doc_blocks[0]["source"]["media_type"] == "application/pdf"

    def test_image_attachment(self):
        p = self._provider()
        data = base64.b64encode(b"fake-img").decode()
        result = p.build_user_content("Schau", [
            {"media_type": "image/jpeg", "data": data},
        ])
        assert isinstance(result, list)
        img_blocks = [b for b in result if b.get("type") == "image"]
        assert len(img_blocks) == 1

    def test_csv_attachment(self):
        p = self._provider()
        csv_data = base64.b64encode(b"a,b\n1,2").decode()
        result = p.build_user_content("Daten", [
            {"media_type": "text/csv", "data": csv_data, "file_name": "test.csv"},
        ])
        assert isinstance(result, list)
        text_blocks = [b for b in result if b.get("type") == "text" and "Inhalt von" in b.get("text", "")]
        assert len(text_blocks) == 1

    def test_skips_empty_data(self):
        p = self._provider()
        result = p.build_user_content("Test", [
            {"media_type": "application/pdf", "data": ""},
        ])
        if isinstance(result, list):
            doc_blocks = [b for b in result if b.get("type") in ("document", "image")]
            assert len(doc_blocks) == 0

    def test_inline_hint_added(self):
        p = self._provider()
        data = base64.b64encode(b"fake").decode()
        result = p.build_user_content("Test", [
            {"media_type": "application/pdf", "data": data},
        ])
        text_blocks = [b for b in result if b.get("type") == "text"]
        user_text = text_blocks[-1]["text"]
        assert "direkt in dieser Nachricht sichtbar" in user_text


class TestClaudeProviderToolResults:
    def _provider(self):
        with patch("anthropic.Anthropic"):
            from gridbert.llm.claude_provider import ClaudeProvider
            return ClaudeProvider(api_key="test", model="claude-test")

    def test_tool_results_format(self):
        p = self._provider()
        results = [
            {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
        ]
        messages = p.build_tool_results_message(results)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == results

    def test_response_to_history_text(self):
        p = self._provider()
        response = LLMResponse(
            content=(LLMTextBlock(text="Hello"),),
            stop_reason="end_turn",
        )
        hist = p.response_to_history(response)
        assert hist["role"] == "assistant"
        assert hist["content"] == [{"type": "text", "text": "Hello"}]

    def test_response_to_history_tool_use(self):
        p = self._provider()
        response = LLMResponse(
            content=(LLMToolUseBlock(id="t1", name="tool", input={"a": 1}),),
            stop_reason="tool_use",
        )
        hist = p.response_to_history(response)
        assert hist["content"][0]["type"] == "tool_use"
        assert hist["content"][0]["id"] == "t1"
        assert hist["content"][0]["name"] == "tool"
        assert hist["content"][0]["input"] == {"a": 1}


# ──────────────────────────────────────────────
# OpenAI Provider
# ──────────────────────────────────────────────


openai = pytest.importorskip("openai", reason="openai not installed")


class TestOpenAIProviderContentBuilding:
    def _provider(self):
        with patch("openai.OpenAI"):
            from gridbert.llm.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key="test", model="gpt-4o")

    def test_plain_text(self):
        p = self._provider()
        assert p.build_user_content("Hallo") == "Hallo"

    def test_image_attachment(self):
        p = self._provider()
        data = base64.b64encode(b"fake-img").decode()
        result = p.build_user_content("Schau", [
            {"media_type": "image/jpeg", "data": data},
        ])
        assert isinstance(result, list)
        img_blocks = [b for b in result if b.get("type") == "image_url"]
        assert len(img_blocks) == 1
        assert "data:image/jpeg;base64," in img_blocks[0]["image_url"]["url"]

    def test_csv_attachment(self):
        p = self._provider()
        csv_data = base64.b64encode(b"a,b\n1,2").decode()
        result = p.build_user_content("Daten", [
            {"media_type": "text/csv", "data": csv_data, "file_name": "test.csv"},
        ])
        assert isinstance(result, list)
        text_blocks = [b for b in result if b.get("type") == "text" and "Inhalt von" in b.get("text", "")]
        assert len(text_blocks) == 1


class TestOpenAIProviderToolResults:
    def _provider(self):
        with patch("openai.OpenAI"):
            from gridbert.llm.openai_provider import OpenAIProvider
            return OpenAIProvider(api_key="test", model="gpt-4o")

    def test_tool_results_format(self):
        p = self._provider()
        results = [
            {"type": "tool_result", "tool_use_id": "call_123", "content": "ok"},
            {"type": "tool_result", "tool_use_id": "call_456", "content": "done"},
        ]
        messages = p.build_tool_results_message(results)
        assert len(messages) == 2
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_123"
        assert messages[0]["content"] == "ok"
        assert messages[1]["tool_call_id"] == "call_456"

    def test_response_to_history_text(self):
        p = self._provider()
        response = LLMResponse(
            content=(LLMTextBlock(text="Hello"),),
            stop_reason="end_turn",
        )
        hist = p.response_to_history(response)
        assert hist["role"] == "assistant"
        assert hist["content"] == "Hello"

    def test_response_to_history_tool_calls(self):
        p = self._provider()
        response = LLMResponse(
            content=(LLMToolUseBlock(id="call_1", name="fn", input={"x": 1}),),
            stop_reason="tool_use",
        )
        hist = p.response_to_history(response)
        assert hist["role"] == "assistant"
        assert hist["content"] is None
        assert len(hist["tool_calls"]) == 1
        tc = hist["tool_calls"][0]
        assert tc["id"] == "call_1"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "fn"
        assert json.loads(tc["function"]["arguments"]) == {"x": 1}


# ──────────────────────────────────────────────
# LLMResponse dataclass
# ──────────────────────────────────────────────


class TestLLMResponse:
    def test_text_parts(self):
        r = LLMResponse(
            content=(LLMTextBlock(text="a"), LLMToolUseBlock(id="t", name="n", input={}), LLMTextBlock(text="b")),
        )
        assert r.text_parts == ["a", "b"]

    def test_tool_uses(self):
        r = LLMResponse(
            content=(LLMTextBlock(text="a"), LLMToolUseBlock(id="t", name="n", input={"x": 1})),
        )
        assert len(r.tool_uses) == 1
        assert r.tool_uses[0].name == "n"

    def test_has_tool_calls(self):
        assert LLMResponse(content=(LLMToolUseBlock(id="t", name="n", input={}),)).has_tool_calls
        assert not LLMResponse(content=(LLMTextBlock(text="hi"),)).has_tool_calls

    def test_empty_response(self):
        r = LLMResponse()
        assert r.text_parts == []
        assert r.tool_uses == []
        assert not r.has_tool_calls
        assert r.stop_reason == "end_turn"


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────


class TestProviderFactory:
    @patch("anthropic.Anthropic")
    def test_create_claude(self, mock_anthropic):
        from gridbert.llm import create_provider
        p = create_provider("claude", "key", "model")
        assert p.provider_name == "claude"

    @pytest.mark.skipif(
        not pytest.importorskip("openai", reason="openai not installed"),
        reason="openai not installed",
    )
    @patch("openai.OpenAI")
    def test_create_openai(self, mock_openai):
        from gridbert.llm import create_provider
        p = create_provider("openai", "key", "model")
        assert p.provider_name == "openai"

    @patch("anthropic.Anthropic")
    def test_default_is_claude(self, mock_anthropic):
        from gridbert.llm import create_provider
        p = create_provider("unknown", "key", "model")
        assert p.provider_name == "claude"
