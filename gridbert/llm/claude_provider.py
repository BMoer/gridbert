# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Claude (Anthropic) LLM Provider."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import anthropic

from gridbert.llm.types import LLMContentBlock, LLMResponse, LLMTextBlock, LLMToolUseBlock

log = logging.getLogger(__name__)

_RETRY_DELAYS = (5, 15, 45)  # seconds — exponential backoff for 429s


class ClaudeProvider:
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "claude"

    def chat(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LLMResponse:
        """Send request to Claude Messages API and return normalized response."""
        response = self._chat_with_retry(system, messages, tools, max_tokens)

        blocks: list[LLMContentBlock] = []
        for block in response.content:
            if block.type == "text":
                blocks.append(LLMTextBlock(text=block.text))
            elif block.type == "tool_use":
                blocks.append(LLMToolUseBlock(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        stop = "end_turn" if response.stop_reason == "end_turn" else "tool_use"
        return LLMResponse(content=tuple(blocks), stop_reason=stop)

    def _chat_with_retry(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> Any:
        """Call Claude API with exponential backoff on 429 rate limit errors."""
        for attempt, delay in enumerate((*_RETRY_DELAYS, 0)):
            try:
                return self._client.messages.create(
                    model=self._model,
                    system=system,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                )
            except anthropic.RateLimitError:
                if delay == 0:
                    raise
                retry_after = delay
                log.warning(
                    "Rate limit (429), Versuch %d/%d — warte %ds",
                    attempt + 1,
                    len(_RETRY_DELAYS),
                    retry_after,
                )
                time.sleep(retry_after)
        # unreachable, but satisfies type checker
        raise RuntimeError("Retry exhausted")  # pragma: no cover

    def build_user_content(
        self,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str | list[dict[str, Any]]:
        """Build Claude-specific user content with optional attachments."""
        if not attachments:
            return text

        content: list[dict[str, Any]] = []
        for attachment in attachments:
            media_type = attachment.get("media_type", "")
            data = attachment.get("data", "")
            if not data:
                continue

            if media_type == "application/pdf":
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": data,
                    },
                })
            elif media_type.startswith("image/"):
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data,
                    },
                })
            elif _is_tabular(media_type, attachment.get("file_name", "")):
                file_name = attachment.get("file_name", "datei")
                file_text = _decode_tabular_file(data, media_type, file_name)
                content.append({
                    "type": "text",
                    "text": f"[Inhalt von {file_name}]\n{file_text}",
                })

        has_docs = any(
            c.get("type") in ("document", "image")
            or (c.get("type") == "text" and c.get("text", "").startswith("[Inhalt von"))
            for c in content
        )
        if has_docs:
            text = (
                f"{text}\n\n[Die angehängten Dateien sind direkt in dieser Nachricht sichtbar. "
                "Du kannst sie direkt lesen und analysieren — du musst KEIN Tool aufrufen um sie zu öffnen.]"
            )

        content.append({"type": "text", "text": text})
        return content

    def build_tool_results_message(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Claude: single user-role message with tool_result content blocks."""
        return [{"role": "user", "content": tool_results}]

    def response_to_history(self, response: LLMResponse) -> dict[str, Any]:
        """Convert response to Claude-format dict for conversation history."""
        content_list: list[dict[str, Any]] = []
        for block in response.content:
            if isinstance(block, LLMTextBlock):
                content_list.append({"type": "text", "text": block.text})
            elif isinstance(block, LLMToolUseBlock):
                content_list.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return {"role": "assistant", "content": content_list}


def _is_tabular(media_type: str, file_name: str) -> bool:
    """Check if the file is a CSV or Excel file."""
    return (
        media_type in (
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        or file_name.endswith((".csv", ".xlsx", ".xls"))
    )


def _decode_tabular_file(data_b64: str, media_type: str, file_name: str) -> str:
    """Decode base64-encoded CSV/Excel to text."""
    if not data_b64:
        return f"[FEHLER: Datei {file_name} ist leer — Upload fehlgeschlagen. Bitte erneut hochladen.]"

    try:
        raw = base64.b64decode(data_b64)
    except Exception as exc:
        log.warning("Base64-Dekodierung fehlgeschlagen für %s: %s", file_name, exc)
        return f"[FEHLER: Datei {file_name} konnte nicht dekodiert werden. Bitte erneut hochladen.]"

    from gridbert.tools.file_utils import decode_tabular_bytes

    return decode_tabular_bytes(raw, media_type, file_name)
