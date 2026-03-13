# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Agent-Loop: LLM-agnostisch mit nativem Tool-Calling."""

from __future__ import annotations

import logging
import re
from typing import Any

from gridbert.agent.tool_registry import ToolRegistry
from gridbert.agent.types import AgentEvent, EventCallback, EventType
from gridbert.config import CLAUDE_MAX_TOKENS
from gridbert.llm import LLMProvider
from gridbert.llm.types import LLMTextBlock, LLMToolUseBlock

log = logging.getLogger(__name__)

MAX_TURNS = 20

# Pattern für Vorschläge am Ende einer Antwort
_SUGGESTION_RE = re.compile(r"^>> (.+)$", re.MULTILINE)


class GridbertAgent:
    """Agentic Loop — provider-agnostic.

    The LLM decides which tools to call. Text is streamed to the frontend.
    Works with any LLM provider that implements the LLMProvider protocol.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_provider: LLMProvider,
        user_memory: list[dict[str, str]] | None = None,
        user_files: list[dict] | None = None,
    ) -> None:
        self._llm = llm_provider
        self._tools = tool_registry
        self._user_memory = user_memory or []
        self._user_files = user_files or []
        # Usage tracking — populated after run()
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

    def _build_system_prompt(self) -> str:
        """System-Prompt mit User-Memory-Kontext aufbauen."""
        from datetime import date

        from gridbert.prompts import SYSTEM_PROMPT_V1

        today = date.today().strftime("%d.%m.%Y")
        parts = [
            SYSTEM_PROMPT_V1,
            f"## Aktuelles Datum\nHeute ist der {today}. "
            "Verwende dieses Datum als Referenz für zeitliche Einordnungen "
            "(z.B. ob ein Tarifstart in der Vergangenheit oder Zukunft liegt).",
        ]

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
            conversation_history: Bisherige Messages (provider format).
            on_event: Callback für SSE-Streaming an das Frontend.
            max_turns: Maximale Anzahl Agent-Turns.
            attachments: Datei-Anhänge (z.B. Bilder für Invoice OCR).

        Returns:
            Die finale Text-Antwort des Agents.
        """
        messages = list(conversation_history or [])

        # User-Nachricht aufbauen (mit optionalen Anhängen)
        user_content = self._llm.build_user_content(user_message, attachments)
        messages.append({"role": "user", "content": user_content})

        system_prompt = self._build_system_prompt()
        tool_definitions = self._tools.definitions()
        final_text = ""
        total_input_tokens = 0
        total_output_tokens = 0

        for turn in range(max_turns):
            log.info("Agent Turn %d/%d", turn + 1, max_turns)

            # Status-Event
            if on_event:
                status_msg = "Gridbert denkt nach..." if turn == 0 else "Gridbert verarbeitet die Ergebnisse..."
                on_event(AgentEvent(
                    type=EventType.STATUS,
                    data={"message": status_msg},
                ))

            response = self._llm.chat(
                system=system_prompt,
                messages=messages,
                tools=tool_definitions,
                max_tokens=CLAUDE_MAX_TOKENS,
            )

            # Accumulate token usage
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Response-Content verarbeiten
            text_parts: list[str] = []
            tool_uses: list[LLMToolUseBlock] = []

            for block in response.content:
                if isinstance(block, LLMTextBlock):
                    text_parts.append(block.text)
                    if on_event:
                        on_event(AgentEvent(
                            type=EventType.TEXT_DELTA,
                            data={"text": block.text},
                        ))
                elif isinstance(block, LLMToolUseBlock):
                    tool_uses.append(block)

            # Assistant-Antwort in History speichern
            messages.append(self._llm.response_to_history(response))

            # Keine Tool-Calls → Finale Antwort
            if response.stop_reason == "end_turn" or not tool_uses:
                raw_text = "\n".join(text_parts)

                # Vorschläge aus dem Text extrahieren
                suggestions = _SUGGESTION_RE.findall(raw_text)
                final_text = _SUGGESTION_RE.sub("", raw_text).rstrip("\n ")

                self.total_input_tokens = total_input_tokens
                self.total_output_tokens = total_output_tokens

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
                tool_name = tool_use.name
                tool_input = tool_use.input

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

                    # Emit live widget event for dashboard updates
                    if tool_name == "add_dashboard_widget":
                        try:
                            import json
                            widget_data = json.loads(result_str)
                            event_type = (
                                EventType.WIDGET_UPDATE
                                if widget_data.get("action") == "updated"
                                else EventType.WIDGET_ADD
                            )
                            on_event(AgentEvent(type=event_type, data=widget_data))
                        except Exception:
                            pass  # Non-critical: dashboard will refresh on next load

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_str,
                })

            # Tool-Ergebnisse zurückspeisen (provider-specific format)
            messages.extend(self._llm.build_tool_results_message(tool_results))

        # Max turns erreicht
        self.total_input_tokens = total_input_tokens
        self.total_output_tokens = total_output_tokens
        final_text = "Ich hab zu viele Schritte gebraucht. Hier ist was ich bisher habe."
        log.warning("Agent hat max_turns (%d) erreicht", max_turns)
        if on_event:
            on_event(AgentEvent(
                type=EventType.DONE,
                data={"final_text": final_text},
            ))
        return final_text
