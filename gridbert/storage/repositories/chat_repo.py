# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Chat Repository — Conversations und Messages."""

from __future__ import annotations

import json

from sqlalchemy import Connection, desc, select

from gridbert.storage.schema import conversations, messages


def create_conversation(conn: Connection, user_id: int, title: str = "") -> int:
    """Neue Conversation anlegen. Gibt die ID zurück."""
    result = conn.execute(
        conversations.insert().values(user_id=user_id, title=title)
    )
    return result.inserted_primary_key[0]


def get_conversations(conn: Connection, user_id: int, limit: int = 20) -> list[dict]:
    """Conversations eines Users laden (neueste zuerst)."""
    rows = conn.execute(
        select(conversations)
        .where(conversations.c.user_id == user_id)
        .order_by(desc(conversations.c.updated_at))
        .limit(limit)
    ).mappings().all()
    return [dict(r) for r in rows]


def add_message(
    conn: Connection,
    conversation_id: int,
    role: str,
    content: str,
    tool_name: str = "",
    tool_input: dict | None = None,
) -> int:
    """Message zu einer Conversation hinzufügen."""
    result = conn.execute(
        messages.insert().values(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name or None,
            tool_input=json.dumps(tool_input) if tool_input else None,
        )
    )
    return result.inserted_primary_key[0]


def get_messages(
    conn: Connection,
    conversation_id: int,
    limit: int = 50,
) -> list[dict]:
    """Messages einer Conversation laden (chronologisch)."""
    rows = conn.execute(
        select(messages)
        .where(messages.c.conversation_id == conversation_id)
        .order_by(messages.c.created_at)
        .limit(limit)
    ).mappings().all()
    return [dict(r) for r in rows]
