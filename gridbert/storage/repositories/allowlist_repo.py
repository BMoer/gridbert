# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Allowlist Repository — Registration email allowlist."""

from __future__ import annotations

from sqlalchemy import Connection, delete, select

from gridbert.storage.schema import registration_allowlist


def list_allowed_emails(conn: Connection) -> list[dict]:
    """All allowed emails from DB."""
    rows = conn.execute(
        select(registration_allowlist).order_by(registration_allowlist.c.created_at)
    ).mappings().all()
    return [dict(r) for r in rows]


def is_email_allowed(conn: Connection, email: str) -> bool:
    """Check if email is in the DB allowlist (case-insensitive)."""
    row = conn.execute(
        select(registration_allowlist.c.id)
        .where(registration_allowlist.c.email == email.strip().lower())
        .limit(1)
    ).first()
    return row is not None


def add_allowed_email(conn: Connection, email: str, added_by: str = "admin") -> int:
    """Add email to allowlist. Returns id."""
    normalized = email.strip().lower()
    result = conn.execute(
        registration_allowlist.insert().values(email=normalized, added_by=added_by)
    )
    conn.commit()
    return result.inserted_primary_key[0]


def remove_allowed_email(conn: Connection, email: str) -> bool:
    """Remove email from allowlist. Returns True if deleted."""
    normalized = email.strip().lower()
    result = conn.execute(
        delete(registration_allowlist)
        .where(registration_allowlist.c.email == normalized)
    )
    conn.commit()
    return result.rowcount > 0
