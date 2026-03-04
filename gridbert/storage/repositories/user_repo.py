# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""User Repository — CRUD für Benutzer."""

from __future__ import annotations

from sqlalchemy import Connection, select

from gridbert.storage.schema import users


def create_user(conn: Connection, email: str, password_hash: str, name: str = "") -> int:
    """Neuen User anlegen. Gibt die User-ID zurück."""
    result = conn.execute(
        users.insert().values(email=email, password_hash=password_hash, name=name)
    )
    return result.inserted_primary_key[0]


def get_user_by_email(conn: Connection, email: str) -> dict | None:
    """User anhand E-Mail laden."""
    row = conn.execute(
        select(users).where(users.c.email == email)
    ).mappings().first()
    return dict(row) if row else None


def get_user_by_id(conn: Connection, user_id: int) -> dict | None:
    """User anhand ID laden."""
    row = conn.execute(
        select(users).where(users.c.id == user_id)
    ).mappings().first()
    return dict(row) if row else None


def update_user(conn: Connection, user_id: int, **fields: str) -> None:
    """User-Felder aktualisieren."""
    allowed = {"name", "plz", "zaehlpunkt"}
    updates = {k: v for k, v in fields.items() if k in allowed and v}
    if updates:
        conn.execute(users.update().where(users.c.id == user_id).values(**updates))
