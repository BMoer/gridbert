# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Chat Endpoint — SSE Streaming vom GridbertAgent."""

from __future__ import annotations

import json
import logging
import queue
import threading
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from gridbert.agent.loop import GridbertAgent
from gridbert.agent.tool_registry import build_core_registry
from gridbert.agent.types import AgentEvent, EventType
from gridbert.api.deps import CurrentUserId, DbConn
from gridbert.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from gridbert.llm import create_provider
from gridbert.storage.repositories.chat_repo import (
    add_message,
    create_conversation,
    get_messages,
)
from gridbert.storage.repositories.file_repo import get_user_files, save_file
from gridbert.storage.repositories.memory_repo import get_user_memories

log = logging.getLogger(__name__)

router = APIRouter()

# After N messages on server key, gently ask user to bring their own key
_NUDGE_AFTER_MESSAGES = 3
_API_KEY_NUDGE = (
    "\n\n---\n"
    "*Kleiner Hinweis: Gridbert ist ein unfunded Hobbyprojekt — "
    "du nutzt gerade meinen API-Schlüssel. "
    "Wenn du einen eigenen hast (z.B. von [Anthropic](https://console.anthropic.com/) "
    "oder [OpenAI](https://platform.openai.com/)), "
    "kannst du ihn unter [Einstellungen](/settings) hinterlegen. "
    "Damit hilfst du mir, Gridbert am Laufen zu halten. Danke!*"
)


class AttachmentData(BaseModel):
    type: str = "document"  # "image" or "document"
    media_type: str = "application/pdf"
    file_name: str = ""
    data: str = ""  # base64


class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
    attachments: list[AttachmentData] | None = None


class ChatStartResponse(BaseModel):
    conversation_id: int


@router.post("/chat")
def chat(
    req: ChatRequest,
    user_id: CurrentUserId,
    conn: DbConn,
) -> StreamingResponse:
    """Chat mit Gridbert — SSE Stream."""
    from gridbert.crypto import decrypt_value
    from gridbert.storage.repositories.user_repo import get_user_llm_config

    # Resolve LLM provider: user key > server key > error
    llm_config = get_user_llm_config(conn, user_id)
    using_server_key = False
    if llm_config["api_key_enc"]:
        api_key = decrypt_value(llm_config["api_key_enc"])
        provider_name = llm_config["provider"] or "claude"
        model = llm_config["model"] or (CLAUDE_MODEL if provider_name == "claude" else "gpt-4o")
    elif ANTHROPIC_API_KEY:
        api_key = ANTHROPIC_API_KEY
        provider_name = "claude"
        model = CLAUDE_MODEL
        using_server_key = True
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NO_API_KEY",
        )

    llm_provider = create_provider(provider_name, api_key, model)

    if using_server_key:
        from gridbert.api.rate_limit import check_rate_limit
        check_rate_limit(user_id)

    log.info("Chat request: message=%r, conv=%s, attachments=%d",
             req.message[:50], req.conversation_id,
             len(req.attachments) if req.attachments else 0)
    if req.attachments:
        for att in req.attachments:
            log.info("  Attachment: type=%s, media=%s, file=%s, data_len=%d",
                     att.type, att.media_type, att.file_name, len(att.data))

    # Conversation erstellen oder bestehende laden
    conversation_id = req.conversation_id
    if conversation_id is None:
        conversation_id = create_conversation(conn, user_id, title=req.message[:80])

    # User-Nachricht persistieren
    add_message(conn, conversation_id, role="user", content=req.message)

    # Datei-Anhänge auf Disk speichern
    if req.attachments:
        for att in req.attachments:
            if att.data:
                try:
                    save_file(conn, user_id, att.file_name, att.media_type, att.data)
                except Exception:
                    log.exception("Fehler beim Speichern von %s", att.file_name)

    # Bisherige Messages laden und zu Claude API Format konvertieren
    history = get_messages(conn, conversation_id, limit=50)
    claude_messages = _history_to_messages(history)

    # User-Memory und gespeicherte Dateien laden
    memories = get_user_memories(conn, user_id)
    user_files = get_user_files(conn, user_id)

    # Initiale Writes committen damit SQLite-Lock freigegeben wird
    conn.commit()

    # Agent bauen — mit User-Kontext für Memory-Tool und Datei-Zugriff
    registry = build_core_registry(user_id=user_id, db_conn=conn, llm_provider=llm_provider)
    agent = GridbertAgent(
        tool_registry=registry,
        llm_provider=llm_provider,
        user_memory=memories,
        user_files=user_files,
    )

    def event_stream():
        """SSE Generator — streamt Events in Echtzeit via Thread + Queue."""
        event_queue: queue.Queue[AgentEvent | None] = queue.Queue()

        def on_event(event: AgentEvent) -> None:
            event_queue.put(event)

        # Attachments für den Agent aufbereiten
        agent_attachments = None
        if req.attachments:
            agent_attachments = [
                {"type": att.type, "media_type": att.media_type, "data": att.data, "file_name": att.file_name}
                for att in req.attachments
            ]

        final_text_holder: list[str] = []

        def run_agent():
            try:
                result = agent.run(
                    user_message=req.message,
                    conversation_history=claude_messages[:-1],
                    on_event=on_event,
                    attachments=agent_attachments,
                )
                final_text_holder.append(result)
            except Exception as exc:
                log.exception("Agent-Fehler")
                event_queue.put(AgentEvent(
                    type=EventType.ERROR,
                    data={"message": str(exc)},
                ))
            finally:
                event_queue.put(None)  # Sentinel: Stream beenden

        # Agent in Background-Thread starten
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        # Events in Echtzeit an den Client senden
        while True:
            event = event_queue.get()
            if event is None:
                break
            yield f"data: {event.model_dump_json()}\n\n"

        # Auf Agent-Thread warten
        thread.join(timeout=5)

        # Nudge: after N messages on server key, ask user to bring their own
        final_text = final_text_holder[0] if final_text_holder else ""
        if using_server_key and final_text:
            msg_count = len([m for m in history if m["role"] == "user"])
            if msg_count >= _NUDGE_AFTER_MESSAGES:
                nudge_event = json.dumps({
                    "type": "text_delta",
                    "data": {"text": _API_KEY_NUDGE},
                })
                yield f"data: {nudge_event}\n\n"
                final_text += _API_KEY_NUDGE

        # Assistant-Antwort persistieren
        try:
            if final_text:
                add_message(conn, conversation_id, role="assistant", content=final_text)
                conn.commit()
        except Exception:
            log.exception("Fehler beim Speichern der Assistant-Antwort")

        # Finale SSE mit Conversation-ID
        done_data = json.dumps({
            "type": "done",
            "data": {"conversation_id": conversation_id},
        })
        yield f"data: {done_data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
def list_conversations(
    user_id: CurrentUserId,
    conn: DbConn,
) -> list[dict[str, Any]]:
    """Alle Conversations eines Users laden."""
    from gridbert.storage.repositories.chat_repo import get_conversations

    return get_conversations(conn, user_id)


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    user_id: CurrentUserId,
    conn: DbConn,
) -> list[dict[str, Any]]:
    """Messages einer Conversation laden."""
    return get_messages(conn, conversation_id)


@router.get("/news")
def list_energy_news() -> list[dict[str, Any]]:
    """Energie-relevante Nachrichten von ORF & Co. laden."""
    from gridbert.tools.energy_monitor import _fetch_energy_news

    try:
        items = _fetch_energy_news()
        return [
            {
                "titel": item.titel,
                "zusammenfassung": item.zusammenfassung,
                "quelle": item.quelle,
                "url": item.url,
                "datum": item.datum.isoformat() if item.datum else None,
                "kategorie": item.kategorie,
            }
            for item in items
        ]
    except Exception:
        log.exception("Fehler beim Laden der Energie-News")
        return []


@router.get("/files")
def list_user_files(
    user_id: CurrentUserId,
    conn: DbConn,
) -> list[dict[str, Any]]:
    """Alle gespeicherten Dateien eines Users laden."""
    return get_user_files(conn, user_id)


@router.get("/memory")
def list_user_memory(
    user_id: CurrentUserId,
    conn: DbConn,
) -> list[dict[str, Any]]:
    """Alle gespeicherten Fakten eines Users laden."""
    return get_user_memories(conn, user_id)


def _history_to_messages(history: list[dict]) -> list[dict[str, Any]]:
    """DB-Messages in Claude API Format konvertieren."""
    claude_messages: list[dict[str, Any]] = []
    for msg in history:
        role = msg["role"]
        if role in ("user", "assistant"):
            claude_messages.append({
                "role": role,
                "content": msg["content"],
            })
    return claude_messages


