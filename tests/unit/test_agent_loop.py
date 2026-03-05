"""Tests for gridbert.agent.loop — _build_user_content, _decode_tabular_file, agent run."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class FakeBlock:
    """Simulates an Anthropic ContentBlock without MagicMock issues."""
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)

from gridbert.agent.loop import (
    GridbertAgent,
    _block_to_dict,
    _build_user_content,
    _decode_tabular_file,
)
from gridbert.agent.types import AgentEvent, EventType


# --- _decode_tabular_file ---


class TestDecodeTabularFile:
    def test_csv_utf8(self):
        csv = "Datum;kWh\n2025-01-01;3.5\n2025-01-02;4.2"
        b64 = base64.b64encode(csv.encode("utf-8")).decode()
        result = _decode_tabular_file(b64, "text/csv", "test.csv")
        assert "Datum;kWh" in result
        assert "3.5" in result

    def test_csv_latin1(self):
        csv = "Datum;kWh\n2025-01-01;3,5\nÄnderung;4,2"
        b64 = base64.b64encode(csv.encode("latin-1")).decode()
        result = _decode_tabular_file(b64, "text/csv", "test.csv")
        assert "Änderung" in result

    def test_csv_utf8_bom(self):
        csv = "Datum;kWh\n2025-01-01;3.5"
        b64 = base64.b64encode(csv.encode("utf-8-sig")).decode()
        result = _decode_tabular_file(b64, "text/csv", "test.csv")
        assert "Datum" in result

    def test_csv_truncation(self):
        csv = "x" * 60_000
        b64 = base64.b64encode(csv.encode()).decode()
        result = _decode_tabular_file(b64, "text/csv", "big.csv")
        assert len(result) < 55_000
        assert "gekürzt" in result

    def test_invalid_base64(self):
        result = _decode_tabular_file("not-valid-base64!!!", "text/csv", "bad.csv")
        assert "FEHLER" in result
        assert "bad.csv" in result

    def test_excel_file(self):
        """Excel decoding requires openpyxl + pandas."""
        import io

        import pandas as pd

        df = pd.DataFrame({"Datum": ["2025-01-01"], "kWh": [3.5]})
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        b64 = base64.b64encode(buf.getvalue()).decode()

        result = _decode_tabular_file(b64, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "test.xlsx")
        assert "Datum" in result
        assert "3.5" in result

    def test_excel_by_filename(self):
        """Detect Excel from filename even with generic media_type."""
        import io

        import pandas as pd

        df = pd.DataFrame({"A": [1, 2]})
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        b64 = base64.b64encode(buf.getvalue()).decode()

        result = _decode_tabular_file(b64, "application/octet-stream", "data.xlsx")
        assert "A" in result

    def test_empty_data(self):
        b64 = base64.b64encode(b"").decode()
        result = _decode_tabular_file(b64, "text/csv", "empty.csv")
        assert "FEHLER" in result
        assert "leer" in result


# --- _build_user_content ---


class TestBuildUserContent:
    def test_no_attachments(self):
        result = _build_user_content("Hallo")
        assert result == "Hallo"

    def test_empty_attachments(self):
        result = _build_user_content("Hallo", [])
        assert result == "Hallo"

    def test_pdf_attachment(self):
        pdf_data = base64.b64encode(b"fake-pdf-content").decode()
        result = _build_user_content("Analysiere das", [
            {"media_type": "application/pdf", "data": pdf_data},
        ])
        assert isinstance(result, list)
        doc_blocks = [b for b in result if b.get("type") == "document"]
        assert len(doc_blocks) == 1
        assert doc_blocks[0]["source"]["media_type"] == "application/pdf"

    def test_image_attachment(self):
        img_data = base64.b64encode(b"fake-image").decode()
        result = _build_user_content("Schau mal", [
            {"media_type": "image/jpeg", "data": img_data},
        ])
        assert isinstance(result, list)
        img_blocks = [b for b in result if b.get("type") == "image"]
        assert len(img_blocks) == 1

    def test_csv_attachment(self):
        csv = "col1,col2\n1,2"
        csv_data = base64.b64encode(csv.encode()).decode()
        result = _build_user_content("Analysiere die Daten", [
            {"media_type": "text/csv", "data": csv_data, "file_name": "lastgang.csv"},
        ])
        assert isinstance(result, list)
        text_blocks = [b for b in result if b.get("type") == "text"]
        # Should have inline CSV text + user message text
        csv_block = [b for b in text_blocks if "Inhalt von" in b.get("text", "")]
        assert len(csv_block) == 1
        assert "col1,col2" in csv_block[0]["text"]

    def test_csv_by_filename(self):
        """CSV detected by filename even with empty media_type."""
        csv = "a,b\n1,2"
        csv_data = base64.b64encode(csv.encode()).decode()
        result = _build_user_content("Test", [
            {"media_type": "", "data": csv_data, "file_name": "data.csv"},
        ])
        assert isinstance(result, list)
        csv_blocks = [b for b in result if b.get("type") == "text" and "Inhalt von" in b.get("text", "")]
        assert len(csv_blocks) == 1

    def test_inline_hint_added(self):
        pdf_data = base64.b64encode(b"fake").decode()
        result = _build_user_content("Analysiere", [
            {"media_type": "application/pdf", "data": pdf_data},
        ])
        text_blocks = [b for b in result if b.get("type") == "text"]
        user_text = text_blocks[-1]["text"]
        assert "direkt in dieser Nachricht sichtbar" in user_text

    def test_skips_empty_data(self):
        result = _build_user_content("Test", [
            {"media_type": "application/pdf", "data": ""},
        ])
        # No valid attachments processed — may return string or list with just text
        if isinstance(result, str):
            assert result == "Test"
        else:
            # List with only the user text block, no doc/image blocks
            doc_blocks = [b for b in result if b.get("type") in ("document", "image")]
            assert len(doc_blocks) == 0

    def test_mixed_attachments(self):
        pdf_data = base64.b64encode(b"pdf").decode()
        img_data = base64.b64encode(b"img").decode()
        csv_data = base64.b64encode(b"a,b\n1,2").decode()
        result = _build_user_content("Alles zusammen", [
            {"media_type": "application/pdf", "data": pdf_data},
            {"media_type": "image/png", "data": img_data},
            {"media_type": "text/csv", "data": csv_data, "file_name": "data.csv"},
        ])
        assert isinstance(result, list)
        types = [b["type"] for b in result]
        assert "document" in types
        assert "image" in types


# --- _block_to_dict ---


class TestBlockToDict:
    def test_text_block(self):
        block = FakeBlock(type="text", text="Hello")
        assert _block_to_dict(block) == {"type": "text", "text": "Hello"}

    def test_tool_use_block(self):
        block = FakeBlock(type="tool_use", id="123", name="compare_tariffs", input={"plz": "1060"})
        result = _block_to_dict(block)
        assert result == {
            "type": "tool_use",
            "id": "123",
            "name": "compare_tariffs",
            "input": {"plz": "1060"},
        }

    def test_unknown_block(self):
        block = FakeBlock(type="thinking")
        assert _block_to_dict(block) == {"type": "thinking"}


# --- GridbertAgent ---


class TestGridbertAgent:
    def _make_agent(self, tool_registry=None, user_memory=None):
        """Create agent with mocked Claude client."""
        registry = tool_registry or MagicMock()
        if tool_registry is None:
            registry.definitions.return_value = []
        agent = GridbertAgent(
            tool_registry=registry,
            user_memory=user_memory,
            model="test-model",
        )
        agent._client = MagicMock()
        return agent

    def test_simple_text_response(self):
        agent = self._make_agent()
        text_block = FakeBlock(type="text", text="Hallo, ich bin Gridbert!")
        response = MagicMock()
        response.content = [text_block]
        response.stop_reason = "end_turn"
        agent._client.messages.create.return_value = response

        events = []
        result = agent.run("Hi", on_event=lambda e: events.append(e))

        assert result == "Hallo, ich bin Gridbert!"
        assert any(e.type == EventType.TEXT_DELTA for e in events)
        assert any(e.type == EventType.DONE for e in events)

    def test_tool_call_loop(self):
        registry = MagicMock()
        registry.definitions.return_value = [{"name": "test_tool"}]
        registry.execute.return_value = '{"result": "ok"}'

        agent = self._make_agent(tool_registry=registry)

        # Turn 1: tool call
        tool_block = FakeBlock(type="tool_use", id="t1", name="test_tool", input={"x": 1})
        response1 = MagicMock()
        response1.content = [tool_block]
        response1.stop_reason = "tool_use"

        # Turn 2: final text
        text_block = FakeBlock(type="text", text="Ergebnis: ok")
        response2 = MagicMock()
        response2.content = [text_block]
        response2.stop_reason = "end_turn"

        agent._client.messages.create.side_effect = [response1, response2]

        events = []
        result = agent.run("Test", on_event=lambda e: events.append(e))

        assert result == "Ergebnis: ok"
        registry.execute.assert_called_once_with("test_tool", {"x": 1})
        assert any(e.type == EventType.TOOL_START for e in events)
        assert any(e.type == EventType.TOOL_RESULT for e in events)

    def test_max_turns_reached(self):
        agent = self._make_agent()

        tool_block = FakeBlock(type="tool_use", id="t1", name="loop_tool", input={})
        response = MagicMock()
        response.content = [tool_block]
        response.stop_reason = "tool_use"
        agent._client.messages.create.return_value = response

        agent._tools.definitions.return_value = [{"name": "loop_tool"}]
        agent._tools.execute.return_value = "still going"

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
        agent = self._make_agent()
        text_block = FakeBlock(type="text", text="Rechnung erkannt.")
        response = MagicMock()
        response.content = [text_block]
        response.stop_reason = "end_turn"
        agent._client.messages.create.return_value = response

        pdf_data = base64.b64encode(b"pdf-content").decode()
        result = agent.run(
            "Analysiere meine Rechnung",
            attachments=[{"media_type": "application/pdf", "data": pdf_data}],
        )
        assert result == "Rechnung erkannt."

        # Verify messages sent to Claude include document block
        call_kwargs = agent._client.messages.create.call_args
        messages = call_kwargs.kwargs["messages"]
        # First message is the user message with attachments
        user_msg = messages[0]
        assert user_msg["role"] == "user"
        assert isinstance(user_msg["content"], list)
        types = [b.get("type") for b in user_msg["content"]]
        assert "document" in types

    def test_status_events_emitted(self):
        agent = self._make_agent()
        text_block = FakeBlock(type="text", text="Antwort.")
        response = MagicMock()
        response.content = [text_block]
        response.stop_reason = "end_turn"
        agent._client.messages.create.return_value = response

        events = []
        agent.run("Hi", on_event=lambda e: events.append(e))

        status_events = [e for e in events if e.type == EventType.STATUS]
        assert len(status_events) >= 1
        assert "denkt nach" in status_events[0].data["message"]

    def test_suggestions_parsed_from_text(self):
        agent = self._make_agent()
        text_with_suggestions = (
            "Hier ist meine Antwort.\n\n"
            ">> Stromtarife vergleichen\n"
            ">> Lastprofil hochladen\n"
            ">> Smart Meter verbinden"
        )
        text_block = FakeBlock(type="text", text=text_with_suggestions)
        response = MagicMock()
        response.content = [text_block]
        response.stop_reason = "end_turn"
        agent._client.messages.create.return_value = response

        events = []
        result = agent.run("Hi", on_event=lambda e: events.append(e))

        # Suggestions stripped from final text
        assert ">> " not in result
        assert "Hier ist meine Antwort." in result

        # Suggestions in DONE event
        done_events = [e for e in events if e.type == EventType.DONE]
        assert len(done_events) == 1
        suggestions = done_events[0].data.get("suggestions", [])
        assert len(suggestions) == 3
        assert "Stromtarife vergleichen" in suggestions

    def test_no_suggestions_when_absent(self):
        agent = self._make_agent()
        text_block = FakeBlock(type="text", text="Einfache Antwort ohne Vorschläge.")
        response = MagicMock()
        response.content = [text_block]
        response.stop_reason = "end_turn"
        agent._client.messages.create.return_value = response

        events = []
        agent.run("Hi", on_event=lambda e: events.append(e))

        done_events = [e for e in events if e.type == EventType.DONE]
        assert "suggestions" not in done_events[0].data
