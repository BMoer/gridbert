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
    _migrate_add_api_usage_columns(_engine)
    _migrate_add_admin_columns(_engine)
    _seed_historical_usage(_engine)
    _seed_allowlist_from_env(_engine)
    _seed_admin_from_env(_engine)
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
        ("nudged_at", "TIMESTAMP", "NULL"),
    ]
    with engine.connect() as conn:
        for col_name, col_type, default in migrations:
            if col_name not in existing:
                conn.execute(sqlalchemy.text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                ))
                log.info("Migration: Added column users.%s", col_name)
        conn.commit()


def _migrate_add_api_usage_columns(engine) -> None:
    """Add server_key column to api_usage if missing (for existing DBs)."""
    import sqlalchemy

    inspector = sqlalchemy.inspect(engine)
    if "api_usage" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("api_usage")}
    if "server_key" not in existing:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text(
                "ALTER TABLE api_usage ADD COLUMN server_key INTEGER DEFAULT 0"
            ))
            conn.commit()
            log.info("Migration: Added column api_usage.server_key")


def _seed_historical_usage(engine) -> None:
    """One-time seed: historical API usage from Anthropic Console (pre-tracking)."""
    from gridbert.storage.schema import api_usage

    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM api_usage WHERE provider = 'seed'")
        ).first()
        if existing:
            return

        # From Anthropic Console as of 2026-03-13:
        # 4,567,426 input + 169,798 output tokens (mostly Haiku, some Sonnet)
        # Estimated cost: Haiku ~$5.25 + Sonnet ~$0.51 = ~$5.76
        conn.execute(api_usage.insert().values(
            user_id=1,
            provider="seed",
            model="claude-haiku-4-5-20251001",
            input_tokens=4_567_426,
            output_tokens=169_798,
            cost_usd=5.76,
            server_key=1,
        ))
        conn.commit()
        log.info("Seeded historical API usage: $5.76 (pre-tracking)")


def _migrate_add_admin_columns(engine) -> None:
    """Add admin columns to users table if missing (for existing DBs)."""
    import sqlalchemy

    inspector = sqlalchemy.inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("users")}
    migrations = [
        ("is_admin", "INTEGER", "0"),
        ("admin_last_login_at", "TIMESTAMP", "NULL"),
    ]
    with engine.connect() as conn:
        for col_name, col_type, default in migrations:
            if col_name not in existing:
                conn.execute(sqlalchemy.text(
                    f"ALTER TABLE users ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                ))
                log.info("Migration: Added column users.%s", col_name)
        conn.commit()


def _seed_admin_from_env(engine) -> None:
    """Mark users from ADMIN_EMAILS as admins (idempotent)."""
    from gridbert.config import ADMIN_EMAILS

    if not ADMIN_EMAILS:
        return

    with engine.connect() as conn:
        for email in ADMIN_EMAILS:
            conn.execute(
                text("UPDATE users SET is_admin = 1 WHERE email = :email AND (is_admin IS NULL OR is_admin = 0)"),
                {"email": email},
            )
        conn.commit()
        log.info("Admin seed: %s", ADMIN_EMAILS)


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
