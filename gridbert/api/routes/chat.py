# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Chat Endpoint — SSE Streaming vom GridbertAgent."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from gridbert.agent.loop import GridbertAgent
from gridbert.agent.tool_registry import build_default_registry
from gridbert.agent.types import AgentEvent
from gridbert.api.deps import CurrentUserId, DbConn
from gridbert.config import ANTHROPIC_API_KEY
from gridbert.storage.repositories.chat_repo import (
    add_message,
    create_conversation,
    get_messages,
)
from gridbert.storage.repositories.memory_repo import get_user_memories

log = logging.getLogger(__name__)

router = APIRouter()


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
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY nicht konfiguriert",
        )

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

    # Bisherige Messages laden und zu Claude API Format konvertieren
    history = get_messages(conn, conversation_id, limit=50)
    claude_messages = _history_to_claude_messages(history)

    # User-Memory laden
    memories = get_user_memories(conn, user_id)

    # Initiale Writes committen damit SQLite-Lock freigegeben wird
    conn.commit()

    # Agent bauen
    registry = build_default_registry()
    agent = GridbertAgent(
        tool_registry=registry,
        user_memory=memories,
    )

    def event_stream():
        """SSE Generator — Agent-Events als Server-Sent Events."""
        events: list[AgentEvent] = []

        def collect_event(event: AgentEvent) -> None:
            events.append(event)

        # Attachments für den Agent aufbereiten
        agent_attachments = None
        if req.attachments:
            agent_attachments = [
                {"type": att.type, "media_type": att.media_type, "data": att.data}
                for att in req.attachments
            ]

        # Agent ausführen (synchron — Tool Calls blockieren)
        final_text = agent.run(
            user_message=req.message,
            conversation_history=claude_messages[:-1],  # letzte User-Message ist schon drin
            on_event=collect_event,
            attachments=agent_attachments,
        )

        # Events als SSE senden
        for event in events:
            yield f"data: {event.model_dump_json()}\n\n"

        # Assistant-Antwort persistieren (gleiche conn, SQLite verträgt keine parallelen Writes)
        try:
            add_message(conn, conversation_id, role="assistant", content=final_text)
            conn.commit()
        except Exception:
            log.exception("Fehler beim Speichern der Assistant-Antwort")

        # Finale SSE
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


def _history_to_claude_messages(history: list[dict]) -> list[dict[str, Any]]:
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


