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
    Column("nudged_at", DateTime, nullable=True),  # when feedback nudge was sent
    Column("is_admin", Integer, default=0),  # 1 = admin user
    Column("admin_last_login_at", DateTime, nullable=True),  # last admin dashboard login
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

# --- Registration Allowlist ---------------------------------------------------

registration_allowlist = Table(
    "registration_allowlist",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("added_by", String, default="admin"),
    Column("created_at", DateTime, server_default=func.now()),
)

# --- Waitlist -----------------------------------------------------------------

waitlist = Table(
    "waitlist",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String, unique=True, nullable=False),
    Column("name", String, default=""),
    Column("created_at", DateTime, server_default=func.now()),
)

# --- API Usage Tracking -------------------------------------------------------

api_usage = Table(
    "api_usage",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("conversation_id", Integer, ForeignKey("conversations.id")),
    Column("provider", String, nullable=False),  # "claude" | "openai"
    Column("model", String, nullable=False),
    Column("input_tokens", Integer, default=0),
    Column("output_tokens", Integer, default=0),
    Column("cost_usd", Float, default=0.0),  # calculated cost
    Column("server_key", Integer, default=0),  # 1 = server key (we pay), 0 = user's own key
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

# --- Switching Requests -------------------------------------------------------

switching_requests = Table(
    "switching_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("status", String, nullable=False, default="pending"),  # pending | in_progress | completed | cancelled
    Column("target_lieferant", String, nullable=False),
    Column("target_tarif", String, nullable=False),
    Column("savings_eur", Float, default=0.0),
    Column("iban", String, default=""),
    Column("email", String, nullable=False),
    Column("zaehlpunkt", String, default=""),
    Column("plz", String, default=""),
    Column("jahresverbrauch_kwh", Float, default=0.0),
    Column("current_lieferant", String, default=""),
    Column("user_name", String, default=""),
    Column("user_address", String, default=""),
    Column("vollmacht_file_id", Integer, ForeignKey("uploaded_files.id"), nullable=True),
    Column("notes", Text, default=""),
    Column("created_at", DateTime, server_default=func.now()),
    Column("completed_at", DateTime, nullable=True),
)

# --- Weekly Updates (sent history) --------------------------------------------

weekly_updates = Table(
    "weekly_updates",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("subject", String, nullable=False),
    Column("body_html", Text, nullable=False),
    Column("linkedin_post", Text, default=""),
    Column("sent_count", Integer, default=0),
    Column("failed_count", Integer, default=0),
    Column("created_at", DateTime, server_default=func.now()),
)
