# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Agent-Loop: Claude API mit nativem Tool-Calling."""

from __future__ import annotations

import base64
import logging
import re
from typing import Any

import anthropic

from gridbert.agent.tool_registry import ToolRegistry
from gridbert.agent.types import AgentEvent, EventCallback, EventType
from gridbert.config import ANTHROPIC_API_KEY, CLAUDE_MAX_TOKENS, CLAUDE_MODEL

log = logging.getLogger(__name__)

MAX_TURNS = 20

# Pattern für Vorschläge am Ende einer Antwort
_SUGGESTION_RE = re.compile(r"^>> (.+)$", re.MULTILINE)


class GridbertAgent:
    """Agentic Loop mit Claude API.

    Claude entscheidet welche Tools aufgerufen werden.
    Text wird token-by-token an das Frontend gestreamt.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        user_memory: list[dict[str, str]] | None = None,
        user_files: list[dict] | None = None,
        model: str = CLAUDE_MODEL,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self._tools = tool_registry
        self._user_memory = user_memory or []
        self._user_files = user_files or []
        self._model = model

    def _build_system_prompt(self) -> str:
        """System-Prompt mit User-Memory-Kontext aufbauen."""
        from gridbert.personality import SYSTEM_PROMPT_V1

        parts = [SYSTEM_PROMPT_V1]

        if self._user_memory:
            memory_lines = "\n".join(
                f"- {m['fact_key']}: {m['fact_value']}"
                for m in self._user_memory
            )
            parts.append(
                f"\n## Was du über diesen User weißt\n{memory_lines}"
            )

        if self._user_files:
            file_lines = "\n".join(
                f"- [{f['id']}] {f['file_name']} ({f['media_type']}, "
                f"{f['size_bytes'] // 1024}KB, {f['created_at']})"
                for f in self._user_files
            )
            parts.append(
                "\n## Gespeicherte Dateien des Users\n"
                "Diese Dateien hat der User in früheren Gesprächen hochgeladen. "
                "Du kannst sie mit get_user_file abrufen wenn sie für die aktuelle "
                "Frage relevant sind.\n" + file_lines
            )

        return "\n\n".join(parts)

    def run(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
        on_event: EventCallback | None = None,
        max_turns: int = MAX_TURNS,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str:
        """Führe den Agent-Loop aus.

        Args:
            user_message: Die Nachricht des Users.
            conversation_history: Bisherige Messages (Claude API format).
            on_event: Callback für SSE-Streaming an das Frontend.
            max_turns: Maximale Anzahl Agent-Turns.
            attachments: Datei-Anhänge (z.B. Bilder für Invoice OCR).

        Returns:
            Die finale Text-Antwort des Agents.
        """
        messages = list(conversation_history or [])

        # User-Nachricht aufbauen (mit optionalen Anhängen)
        user_content = _build_user_content(user_message, attachments)
        messages.append({"role": "user", "content": user_content})

        system_prompt = self._build_system_prompt()
        tool_definitions = self._tools.definitions()
        final_text = ""

        for turn in range(max_turns):
            log.info("Agent Turn %d/%d", turn + 1, max_turns)

            # Status-Event: Claude denkt nach
            if on_event:
                status_msg = "Gridbert denkt nach..." if turn == 0 else "Gridbert verarbeitet die Ergebnisse..."
                on_event(AgentEvent(
                    type=EventType.STATUS,
                    data={"message": status_msg},
                ))

            response = self._client.messages.create(
                model=self._model,
                system=system_prompt,
                messages=messages,
                tools=tool_definitions,
                max_tokens=CLAUDE_MAX_TOKENS,
            )

            # Response-Content verarbeiten
            assistant_content = response.content
            text_parts: list[str] = []
            tool_uses: list[dict[str, Any]] = []

            for block in assistant_content:
                if block.type == "text":
                    text_parts.append(block.text)
                    if on_event:
                        on_event(AgentEvent(
                            type=EventType.TEXT_DELTA,
                            data={"text": block.text},
                        ))
                elif block.type == "tool_use":
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            # Assistant-Antwort in History speichern
            messages.append({
                "role": "assistant",
                "content": [_block_to_dict(b) for b in assistant_content],
            })

            # Keine Tool-Calls → Finale Antwort
            if response.stop_reason == "end_turn" or not tool_uses:
                raw_text = "\n".join(text_parts)

                # Vorschläge aus dem Text extrahieren
                suggestions = _SUGGESTION_RE.findall(raw_text)
                final_text = _SUGGESTION_RE.sub("", raw_text).rstrip("\n ")

                if on_event:
                    done_data: dict[str, Any] = {"final_text": final_text}
                    if suggestions:
                        done_data["suggestions"] = suggestions
                    on_event(AgentEvent(
                        type=EventType.DONE,
                        data=done_data,
                    ))
                return final_text

            # Tool-Calls ausführen
            tool_results: list[dict[str, Any]] = []
            for tool_use in tool_uses:
                tool_name = tool_use["name"]
                tool_input = tool_use["input"]

                if on_event:
                    on_event(AgentEvent(
                        type=EventType.TOOL_START,
                        data={"tool": tool_name, "input": tool_input},
                    ))

                log.info("Tool aufrufen: %s", tool_name)
                result_str = self._tools.execute(tool_name, tool_input)

                if on_event:
                    on_event(AgentEvent(
                        type=EventType.TOOL_RESULT,
                        data={
                            "tool": tool_name,
                            "summary": result_str[:500],
                        },
                    ))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "content": result_str,
                })

            # Tool-Ergebnisse als User-Nachricht zurückspeisen
            messages.append({"role": "user", "content": tool_results})

        # Max turns erreicht
        final_text = "Ich hab zu viele Schritte gebraucht. Hier ist was ich bisher habe."
        log.warning("Agent hat max_turns (%d) erreicht", max_turns)
        if on_event:
            on_event(AgentEvent(
                type=EventType.DONE,
                data={"final_text": final_text},
            ))
        return final_text


def _build_user_content(
    text: str,
    attachments: list[dict[str, Any]] | None = None,
) -> str | list[dict[str, Any]]:
    """User-Content mit optionalen Bild-/Dokument-Anhängen aufbauen."""
    if not attachments:
        return text

    content: list[dict[str, Any]] = []
    for attachment in attachments:
        media_type = attachment.get("media_type", "")
        data = attachment.get("data", "")
        if not data:
            continue

        if media_type == "application/pdf":
            # PDF — Claude Document support
            content.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": data,
                },
            })
        elif media_type.startswith("image/"):
            # Bild — Claude Vision
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": data,
                },
            })
        elif media_type in ("text/csv", "application/vnd.ms-excel",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ) or attachment.get("file_name", "").endswith((".csv", ".xlsx", ".xls")):
            # CSV/Excel — als Text dekodieren und inline einfügen
            file_name = attachment.get("file_name", "datei")
            file_text = _decode_tabular_file(data, media_type, file_name)
            content.append({
                "type": "text",
                "text": f"[Inhalt von {file_name}]\n{file_text}",
            })

    # Hinweis an Claude: angehängte Daten sind direkt sichtbar
    has_docs = any(c.get("type") in ("document", "image") or
                   (c.get("type") == "text" and c.get("text", "").startswith("[Inhalt von"))
                   for c in content)
    if has_docs:
        text = (
            f"{text}\n\n[Die angehängten Dateien sind direkt in dieser Nachricht sichtbar. "
            "Du kannst sie direkt lesen und analysieren — du musst KEIN Tool aufrufen um sie zu öffnen.]"
        )

    content.append({"type": "text", "text": text})
    return content


def _decode_tabular_file(data_b64: str, media_type: str, file_name: str) -> str:
    """Base64-kodierte CSV/Excel-Datei dekodieren und als Text zurückgeben.

    Returns error message (not empty string) on failure so Claude knows something went wrong.
    """
    if not data_b64:
        return f"[FEHLER: Datei {file_name} ist leer — Upload fehlgeschlagen. Bitte erneut hochladen.]"

    try:
        raw = base64.b64decode(data_b64)
    except Exception as exc:
        log.warning("Base64-Dekodierung fehlgeschlagen für %s: %s", file_name, exc)
        return f"[FEHLER: Datei {file_name} konnte nicht dekodiert werden. Bitte erneut hochladen.]"

    from gridbert.tools.file_utils import decode_tabular_bytes

    return decode_tabular_bytes(raw, media_type, file_name)


def _block_to_dict(block: Any) -> dict[str, Any]:
    """Anthropic ContentBlock zu dict konvertieren für Message-History."""
    if block.type == "text":
        return {"type": "text", "text": block.text}
    elif block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    return {"type": block.type}
