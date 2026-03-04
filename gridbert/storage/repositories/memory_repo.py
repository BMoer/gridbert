# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Memory Repository — Persistente User-Fakten für Gridbert."""

from __future__ import annotations

from sqlalchemy import Connection, select

from gridbert.storage.schema import user_memory


def upsert_memory(
    conn: Connection,
    user_id: int,
    fact_key: str,
    fact_value: str,
    source: str = "",
) -> None:
    """Fakt speichern oder aktualisieren (Upsert auf user_id + fact_key)."""
    existing = conn.execute(
        select(user_memory).where(
            user_memory.c.user_id == user_id,
            user_memory.c.fact_key == fact_key,
        )
    ).first()

    if existing:
        conn.execute(
            user_memory.update()
            .where(user_memory.c.id == existing.id)
            .values(fact_value=fact_value, source=source)
        )
    else:
        conn.execute(
            user_memory.insert().values(
                user_id=user_id,
                fact_key=fact_key,
                fact_value=fact_value,
                source=source,
            )
        )


def get_user_memories(conn: Connection, user_id: int) -> list[dict]:
    """Alle Fakten eines Users laden."""
    rows = conn.execute(
        select(user_memory)
        .where(user_memory.c.user_id == user_id)
        .order_by(user_memory.c.fact_key)
    ).mappings().all()
    return [dict(r) for r in rows]


def delete_memory(conn: Connection, user_id: int, fact_key: str) -> None:
    """Einen Fakt löschen."""
    conn.execute(
        user_memory.delete().where(
            user_memory.c.user_id == user_id,
            user_memory.c.fact_key == fact_key,
        )
    )
