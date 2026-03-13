# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""OpenAI LLM Provider."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

from gridbert.llm.types import LLMContentBlock, LLMResponse, LLMTextBlock, LLMToolUseBlock, LLMUsage

log = logging.getLogger(__name__)

_RETRY_DELAYS = (5, 15, 45)  # seconds — exponential backoff for 429s


class OpenAIProvider:
    """OpenAI API provider (GPT-4o, etc.)."""

    def __init__(self, api_key: str, model: str) -> None:
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    def chat(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LLMResponse:
        """Send request to OpenAI Chat Completions API."""
        oai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        oai_messages.extend(_convert_messages_to_openai(messages))

        oai_tools = (
            [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["input_schema"],
                    },
                }
                for t in tools
            ]
            if tools
            else None
        )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": oai_messages,
            "max_tokens": max_tokens,
        }
        if oai_tools:
            kwargs["tools"] = oai_tools

        response = self._completions_with_retry(**kwargs)
        choice = response.choices[0]

        blocks: list[LLMContentBlock] = []
        if choice.message.content:
            blocks.append(LLMTextBlock(text=choice.message.content))

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                blocks.append(LLMToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))

        stop = "tool_use" if choice.finish_reason == "tool_calls" else "end_turn"
        usage = LLMUsage(
            input_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
            output_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
        )
        return LLMResponse(content=tuple(blocks), stop_reason=stop, usage=usage)

    def _completions_with_retry(self, **kwargs: Any) -> Any:
        """Call OpenAI API with exponential backoff on 429 rate limit errors."""
        import openai

        for attempt, delay in enumerate((*_RETRY_DELAYS, 0)):
            try:
                return self._client.chat.completions.create(**kwargs)
            except openai.RateLimitError:
                if delay == 0:
                    raise
                log.warning(
                    "Rate limit (429), Versuch %d/%d — warte %ds",
                    attempt + 1,
                    len(_RETRY_DELAYS),
                    delay,
                )
                time.sleep(delay)
        raise RuntimeError("Retry exhausted")  # pragma: no cover

    def build_user_content(
        self,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str | list[dict[str, Any]]:
        """Build OpenAI-specific user content with optional attachments."""
        if not attachments:
            return text

        content: list[dict[str, Any]] = []
        for attachment in attachments:
            media_type = attachment.get("media_type", "")
            data = attachment.get("data", "")
            if not data:
                continue

            if media_type == "application/pdf":
                # OpenAI has no native PDF support — extract text
                pdf_text = _pdf_b64_to_text(data)
                file_name = attachment.get("file_name", "document.pdf")
                content.append({
                    "type": "text",
                    "text": f"[Inhalt von {file_name}]\n{pdf_text}",
                })
            elif media_type.startswith("image/"):
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{data}",
                    },
                })
            elif _is_tabular(media_type, attachment.get("file_name", "")):
                file_name = attachment.get("file_name", "datei")
                file_text = _decode_tabular_file(data, media_type, file_name)
                content.append({
                    "type": "text",
                    "text": f"[Inhalt von {file_name}]\n{file_text}",
                })

        has_docs = len(content) > 0
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
        """OpenAI: separate tool-role messages for each result."""
        return [
            {
                "role": "tool",
                "tool_call_id": tr["tool_use_id"],
                "content": tr["content"],
            }
            for tr in tool_results
        ]

    def response_to_history(self, response: LLMResponse) -> dict[str, Any]:
        """Convert response to OpenAI-format dict for conversation history."""
        result: dict[str, Any] = {"role": "assistant"}
        text_parts = response.text_parts
        result["content"] = "\n".join(text_parts) if text_parts else None

        tool_uses = response.tool_uses
        if tool_uses:
            result["tool_calls"] = [
                {
                    "id": t.id,
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "arguments": json.dumps(t.input),
                    },
                }
                for t in tool_uses
            ]
        return result


def _convert_messages_to_openai(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Claude-style conversation history to OpenAI format.

    Claude uses nested content blocks; OpenAI uses flat messages with tool_calls.
    """
    result: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user":
            # Could be string or list of content blocks
            if isinstance(content, str):
                result.append({"role": "user", "content": content})
            elif isinstance(content, list):
                # Check if these are tool_result blocks (Claude format)
                if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    for block in content:
                        result.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id", ""),
                            "content": block.get("content", ""),
                        })
                else:
                    # Mixed content (text, images, etc.) — convert to OpenAI format
                    oai_content = _convert_content_blocks(content)
                    result.append({"role": "user", "content": oai_content})

        elif role == "assistant":
            if isinstance(content, str):
                result.append({"role": "assistant", "content": content})
            elif isinstance(content, list):
                assistant_msg: dict[str, Any] = {"role": "assistant"}
                texts = []
                tool_calls = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
                                "id": block.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": json.dumps(block.get("input", {})),
                                },
                            })
                assistant_msg["content"] = "\n".join(texts) if texts else None
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                result.append(assistant_msg)

        elif role == "tool":
            # Already in OpenAI format
            result.append(msg)

    return result


def _convert_content_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Claude content blocks (image, document, text) to OpenAI format."""
    result: list[dict[str, Any]] = []
    for block in blocks:
        block_type = block.get("type", "")
        if block_type == "text":
            result.append({"type": "text", "text": block.get("text", "")})
        elif block_type == "image":
            source = block.get("source", {})
            media_type = source.get("media_type", "image/png")
            data = source.get("data", "")
            result.append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{data}"},
            })
        elif block_type == "document":
            # OpenAI has no native document support — extract text
            source = block.get("source", {})
            data = source.get("data", "")
            result.append({
                "type": "text",
                "text": f"[PDF Dokument]\n{_pdf_b64_to_text(data)}",
            })
    return result


def _pdf_b64_to_text(data_b64: str) -> str:
    """Extract text from a base64-encoded PDF using pdfplumber."""
    try:
        import io

        import pdfplumber

        raw = base64.b64decode(data_b64)
        pages_text = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        return "\n\n".join(pages_text) if pages_text else "[PDF enthält keinen extrahierbaren Text.]"
    except Exception as exc:
        log.warning("PDF-Textextraktion fehlgeschlagen: %s", exc)
        return f"[FEHLER: PDF konnte nicht gelesen werden: {exc}]"


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
        return f"[FEHLER: Datei {file_name} ist leer.]"

    try:
        raw = base64.b64decode(data_b64)
    except Exception as exc:
        log.warning("Base64-Dekodierung fehlgeschlagen für %s: %s", file_name, exc)
        return f"[FEHLER: Datei {file_name} konnte nicht dekodiert werden.]"

    from gridbert.tools.file_utils import decode_tabular_bytes

    return decode_tabular_bytes(raw, media_type, file_name)
