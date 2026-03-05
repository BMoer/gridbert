# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Datenbank-Schema — SQLAlchemy Core Tabellendefinitionen."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
)

metadata = MetaData()

# --- Users --------------------------------------------------------------------

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("password_hash", String, nullable=False),
    Column("name", String, default=""),
    Column("plz", String, default=""),
    Column("zaehlpunkt", String, default=""),
    Column("llm_provider", String, default=""),  # "claude" | "openai" | ""
    Column("llm_api_key_enc", Text, default=""),  # Fernet-encrypted API key
    Column("llm_model", String, default=""),  # e.g. "claude-haiku-4-5-20251001", "gpt-4o"
    Column("created_at", DateTime, server_default=func.now()),
)

# --- Conversations ------------------------------------------------------------

conversations = Table(
    "conversations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("title", String, default=""),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
)

# --- Messages -----------------------------------------------------------------

messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", Integer, ForeignKey("conversations.id"), nullable=False),
    Column("role", String, nullable=False),  # user | assistant | tool_result
    Column("content", Text, nullable=False),
    Column("tool_name", String),
    Column("tool_input", Text),  # JSON
    Column("created_at", DateTime, server_default=func.now()),
)

# --- Analyses -----------------------------------------------------------------

analyses = Table(
    "analyses",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("conversation_id", Integer, ForeignKey("conversations.id")),
    Column("report_markdown", Text),
    Column("report_data", Text),  # JSON (SavingsReport serialisiert)
    Column("created_at", DateTime, server_default=func.now()),
)

# --- User Memory --------------------------------------------------------------

user_memory = Table(
    "user_memory",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("fact_key", String, nullable=False),
    Column("fact_value", String, nullable=False),
    Column("source", String, default=""),  # invoice_2024, user_said, etc.
    Column("created_at", DateTime, server_default=func.now()),
    # UNIQUE(user_id, fact_key) — handled via upsert logic
)

# --- Uploaded Files -----------------------------------------------------------

uploaded_files = Table(
    "uploaded_files",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("file_name", String, nullable=False),
    Column("media_type", String, nullable=False),
    Column("file_hash", String, nullable=False),  # SHA-256 for dedup
    Column("disk_path", String, nullable=False),  # relative path under UPLOAD_DIR
    Column("size_bytes", Integer, default=0),
    Column("created_at", DateTime, server_default=func.now()),
)

# --- Dashboard Widgets --------------------------------------------------------

dashboard_widgets = Table(
    "dashboard_widgets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("widget_type", String, nullable=False),
    Column("position", Integer, default=0),
    Column("config", Text, default="{}"),  # JSON
    Column("created_at", DateTime, server_default=func.now()),
)
