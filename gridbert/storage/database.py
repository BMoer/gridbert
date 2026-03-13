# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Datenbank-Verbindung und Session-Management."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Connection, create_engine, text

from gridbert.config import DATABASE_URL

log = logging.getLogger(__name__)

# SQLite: Verzeichnis sicherstellen
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

_engine = create_engine(
    DATABASE_URL,
    echo=False,
    # SQLite braucht check_same_thread=False für Multi-Thread
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def get_engine():
    return _engine


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """Datenbank-Connection als Context Manager."""
    with _engine.connect() as conn:
        yield conn
        conn.commit()


def init_db() -> None:
    """Schema initialisieren (für Entwicklung ohne Alembic)."""
    from gridbert.storage.schema import metadata

    metadata.create_all(_engine)
    _migrate_add_llm_columns(_engine)
    _seed_allowlist_from_env(_engine)
    log.info("Datenbank initialisiert: %s", DATABASE_URL)


def _migrate_add_llm_columns(engine) -> None:
    """Add LLM provider columns to users table if missing (for existing DBs)."""
    import sqlalchemy

    inspector = sqlalchemy.inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("users")}
    migrations = [
        ("llm_provider", "VARCHAR", "''"),
        ("llm_api_key_enc", "TEXT", "''"),
        ("llm_model", "VARCHAR", "''"),
    ]
    with engine.connect() as conn:
        for col_name, col_type, default in migrations:
            if col_name not in existing:
                conn.execute(sqlalchemy.text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                ))
                log.info("Migration: Added column users.%s", col_name)
        conn.commit()


def _seed_allowlist_from_env(engine) -> None:
    """Copy REGISTRATION_ALLOWLIST env var entries into DB (idempotent)."""
    from gridbert.config import REGISTRATION_ALLOWLIST
    from gridbert.storage.schema import registration_allowlist

    if not REGISTRATION_ALLOWLIST:
        return

    with engine.connect() as conn:
        for email in REGISTRATION_ALLOWLIST:
            existing = conn.execute(
                text("SELECT id FROM registration_allowlist WHERE email = :email"),
                {"email": email},
            ).first()
            if not existing:
                conn.execute(
                    registration_allowlist.insert().values(
                        email=email, added_by="env_seed"
                    )
                )
                log.info("Allowlist seed: %s", email)
        conn.commit()
