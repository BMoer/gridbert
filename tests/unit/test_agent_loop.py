"""Tests for gridbert.agent.loop — GridbertAgent with LLMProvider abstraction."""

from __future__ import annotations

import base64
from typing import Any
from unittest.mock import MagicMock

import pytest

from gridbert.agent.loop import GridbertAgent
from gridbert.agent.types import AgentEvent, EventType
from gridbert.llm.types import LLMResponse, LLMTextBlock, LLMToolUseBlock


def _make_provider(responses: list[LLMResponse] | None = None) -> MagicMock:
    """Create a mock LLMProvider."""
    provider = MagicMock()
    provider.provider_name = "claude"
    provider.build_user_content.side_effect = lambda text, att=None: text
    provider.response_to_history.side_effect = lambda r: {
        "role": "assistant",
        "content": [
            {"type": "text", "text": b.text}
            for b in r.content
            if isinstance(b, LLMTextBlock)
        ],
    }
    provider.build_tool_results_message.side_effect = lambda results: [
        {"role": "user", "content": results}
    ]
    if responses:
        provider.chat.side_effect = responses
    return provider


class TestGridbertAgent:
    def _make_agent(
        self,
        tool_registry=None,
        user_memory=None,
        responses: list[LLMResponse] | None = None,
    ):
        """Create agent with mocked LLM provider."""
        registry = tool_registry or MagicMock()
        if tool_registry is None:
            registry.definitions.return_value = []
        provider = _make_provider(responses)
        agent = GridbertAgent(
            tool_registry=registry,
            llm_provider=provider,
            user_memory=user_memory,
        )
        return agent

    def test_simple_text_response(self):
        response = LLMResponse(
            content=(LLMTextBlock(text="Hallo, ich bin Gridbert!"),),
            stop_reason="end_turn",
        )
        agent = self._make_agent(responses=[response])

        events: list[AgentEvent] = []
        result = agent.run("Hi", on_event=lambda e: events.append(e))

        assert result == "Hallo, ich bin Gridbert!"
        assert any(e.type == EventType.TEXT_DELTA for e in events)
        assert any(e.type == EventType.DONE for e in events)

    def test_tool_call_loop(self):
        registry = MagicMock()
        registry.definitions.return_value = [{"name": "test_tool"}]
        registry.execute.return_value = '{"result": "ok"}'

        response1 = LLMResponse(
            content=(LLMToolUseBlock(id="t1", name="test_tool", input={"x": 1}),),
            stop_reason="tool_use",
        )
        response2 = LLMResponse(
            content=(LLMTextBlock(text="Ergebnis: ok"),),
            stop_reason="end_turn",
        )

        provider = _make_provider([response1, response2])
        agent = GridbertAgent(
            tool_registry=registry,
            llm_provider=provider,
        )

        events: list[AgentEvent] = []
        result = agent.run("Test", on_event=lambda e: events.append(e))

        assert result == "Ergebnis: ok"
        registry.execute.assert_called_once_with("test_tool", {"x": 1})
        assert any(e.type == EventType.TOOL_START for e in events)
        assert any(e.type == EventType.TOOL_RESULT for e in events)

    def test_max_turns_reached(self):
        tool_response = LLMResponse(
            content=(LLMToolUseBlock(id="t1", name="loop_tool", input={}),),
            stop_reason="tool_use",
        )

        registry = MagicMock()
        registry.definitions.return_value = [{"name": "loop_tool"}]
        registry.execute.return_value = "still going"

        provider = _make_provider([tool_response] * 5)
        agent = GridbertAgent(
            tool_registry=registry,
            llm_provider=provider,
        )

        result = agent.run("Test", max_turns=2)
        assert "zu viele Schritte" in result

    def test_user_memory_in_system_prompt(self):
        agent = self._make_agent(user_memory=[
            {"fact_key": "Name", "fact_value": "Benjamin"},
            {"fact_key": "PLZ", "fact_value": "1060"},
        ])
        prompt = agent._build_system_prompt()
        assert "Benjamin" in prompt
        assert "1060" in prompt
        assert "Was du über diesen User weißt" in prompt

    def test_no_user_memory(self):
        agent = self._make_agent(user_memory=[])
        prompt = agent._build_system_prompt()
        assert "Was du über diesen User weißt" not in prompt

    def test_attachments_passed_through(self):
        response = LLMResponse(
            content=(LLMTextBlock(text="Rechnung erkannt."),),
            stop_reason="end_turn",
        )
        agent = self._make_agent(responses=[response])

        pdf_data = base64.b64encode(b"pdf-content").decode()
        result = agent.run(
            "Analysiere meine Rechnung",
            attachments=[{"media_type": "application/pdf", "data": pdf_data}],
        )
        assert result == "Rechnung erkannt."

        # Verify build_user_content was called with attachments
        agent._llm.build_user_content.assert_called_once()
        call_args = agent._llm.build_user_content.call_args
        assert call_args[0][1] == [{"media_type": "application/pdf", "data": pdf_data}]

    def test_status_events_emitted(self):
        response = LLMResponse(
            content=(LLMTextBlock(text="Antwort."),),
            stop_reason="end_turn",
        )
        agent = self._make_agent(responses=[response])

        events: list[AgentEvent] = []
        agent.run("Hi", on_event=lambda e: events.append(e))

        status_events = [e for e in events if e.type == EventType.STATUS]
        assert len(status_events) >= 1
        assert "denkt nach" in status_events[0].data["message"]

    def test_suggestions_parsed_from_text(self):
        text = (
            "Hier ist meine Antwort.\n\n"
            ">> Stromtarife vergleichen\n"
            ">> Lastprofil hochladen\n"
            ">> Smart Meter verbinden"
        )
        response = LLMResponse(
            content=(LLMTextBlock(text=text),),
            stop_reason="end_turn",
        )
        agent = self._make_agent(responses=[response])

        events: list[AgentEvent] = []
        result = agent.run("Hi", on_event=lambda e: events.append(e))

        assert ">> " not in result
        assert "Hier ist meine Antwort." in result

        done_events = [e for e in events if e.type == EventType.DONE]
        assert len(done_events) == 1
        suggestions = done_events[0].data.get("suggestions", [])
        assert len(suggestions) == 3
        assert "Stromtarife vergleichen" in suggestions

    def test_no_suggestions_when_absent(self):
        response = LLMResponse(
            content=(LLMTextBlock(text="Einfache Antwort ohne Vorschläge."),),
            stop_reason="end_turn",
        )
        agent = self._make_agent(responses=[response])

        events: list[AgentEvent] = []
        agent.run("Hi", on_event=lambda e: events.append(e))

        done_events = [e for e in events if e.type == EventType.DONE]
        assert "suggestions" not in done_events[0].data
