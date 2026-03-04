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
    log.info("Datenbank initialisiert: %s", DATABASE_URL)
