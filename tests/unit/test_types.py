"""Tests for gridbert.agent.types."""

from __future__ import annotations

import json

from gridbert.agent.types import AgentEvent, EventType, Role, ToolDefinition, ToolResult


class TestEventType:
    def test_values(self):
        assert EventType.TEXT_DELTA == "text_delta"
        assert EventType.TOOL_START == "tool_start"
        assert EventType.TOOL_RESULT == "tool_result"
        assert EventType.STATUS == "status"
        assert EventType.DONE == "done"
        assert EventType.ERROR == "error"


class TestRole:
    def test_values(self):
        assert Role.USER == "user"
        assert Role.ASSISTANT == "assistant"


class TestAgentEvent:
    def test_serialization(self):
        event = AgentEvent(type=EventType.TEXT_DELTA, data={"text": "Hallo"})
        json_str = event.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["type"] == "text_delta"
        assert parsed["data"]["text"] == "Hallo"

    def test_tool_start_event(self):
        event = AgentEvent(
            type=EventType.TOOL_START,
            data={"tool": "compare_tariffs", "input": {"plz": "1060"}},
        )
        d = event.model_dump()
        assert d["type"] == "tool_start"
        assert d["data"]["tool"] == "compare_tariffs"

    def test_done_event(self):
        event = AgentEvent(type=EventType.DONE, data={"final_text": "Fertig."})
        assert event.type == EventType.DONE


class TestToolDefinition:
    def test_structure(self):
        td = ToolDefinition(
            name="test",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
        )
        assert td.name == "test"
        assert td.description == "A test tool"


class TestToolResult:
    def test_success(self):
        tr = ToolResult(tool_use_id="123", content="result")
        assert tr.is_error is False

    def test_error(self):
        tr = ToolResult(tool_use_id="123", content="boom", is_error=True)
        assert tr.is_error is True
