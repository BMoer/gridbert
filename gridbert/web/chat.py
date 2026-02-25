# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Chat-Backend — Ollama Q&A über den Einsparungs-Report."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import httpx

from gridbert.config import OLLAMA_HOST, OLLAMA_MODEL

log = logging.getLogger(__name__)

_CHAT_SYSTEM_PROMPT = """\
Du bist Gridbert, ein persönlicher Energie-Agent für österreichische Konsumenten.
Der User hat gerade seinen Einsparungs-Report bekommen und hat Rückfragen.

## Regeln
- Beantworte Fragen zum Report, zu Tarifen, zu Energiegemeinschaften, zum Wechselprozess.
- Bleib bei den Fakten aus dem Report — erfinde keine Zahlen.
- Wenn du etwas nicht weißt, sag das ehrlich.
- Antworte kurz und direkt (2-4 Sätze), außer der User fragt explizit nach Details.
- Alle Preise in Österreich sind brutto (inkl. 20% MwSt).
- Du darfst den Energienerd raushängen lassen, aber übertreib nicht.

## Report-Kontext
{report_context}
"""


def chat_stream(
    message: str,
    report_markdown: str,
    chat_history: list[dict] | None = None,
) -> Iterator[str]:
    """Streaming-Antwort von Ollama mit Report-Kontext.

    Yields Token für Token (für SSE).
    """
    chat_history = chat_history or []

    system_prompt = _CHAT_SYSTEM_PROMPT.format(report_context=report_markdown)

    # Ollama Messages aufbauen
    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-10:]:  # Max 10 Messages History
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=10.0)) as client:
            with client.stream(
                "POST",
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log.error("Chat-Fehler: %s", e)
        yield f"\n\n_Fehler bei der Antwort: {e}_"
