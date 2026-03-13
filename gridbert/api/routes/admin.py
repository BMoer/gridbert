# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Admin Routes — Usage tracking, analytics, allowlist management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc, func, select

from gridbert.api.deps import DbConn
from gridbert.storage.schema import conversations, messages, users

router = APIRouter()

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

_DASHBOARD_HTML = (
    Path(__file__).resolve().parent.parent / "admin_dashboard.html"
).read_text(encoding="utf-8")


def _require_admin(token: str) -> None:
    """Verify admin token."""
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized",
        )


# --- Dashboard HTML -----------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(token: str = Query(...)) -> HTMLResponse:
    """Serve standalone admin dashboard."""
    _require_admin(token)
    return HTMLResponse(_DASHBOARD_HTML)


# --- Analytics ----------------------------------------------------------------

@router.get("/overview")
def admin_overview(
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """High-level stats: user count, message count, active users."""
    _require_admin(token)

    user_count = conn.execute(select(func.count()).select_from(users)).scalar()
    msg_count = conn.execute(select(func.count()).select_from(messages)).scalar()
    conv_count = conn.execute(select(func.count()).select_from(conversations)).scalar()

    user_stats = conn.execute(
        select(
            users.c.id,
            users.c.email,
            users.c.name,
            users.c.created_at,
            func.count(messages.c.id).label("message_count"),
        )
        .select_from(
            users
            .outerjoin(conversations, conversations.c.user_id == users.c.id)
            .outerjoin(messages, messages.c.conversation_id == conversations.c.id)
        )
        .group_by(users.c.id)
        .order_by(desc("message_count"))
        .limit(20)
    ).mappings().all()

    return {
        "total_users": user_count,
        "total_messages": msg_count,
        "total_conversations": conv_count,
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "name": u["name"],
                "created_at": str(u["created_at"]) if u["created_at"] else None,
                "message_count": u["message_count"],
            }
            for u in user_stats
        ],
    }


@router.get("/activity")
def admin_activity(
    token: str = Query(...),
    limit: int = Query(50, le=200),
    conn: DbConn = ...,
) -> list[dict[str, Any]]:
    """Recent messages across all users (newest first)."""
    _require_admin(token)

    rows = conn.execute(
        select(
            messages.c.id,
            messages.c.role,
            messages.c.content,
            messages.c.tool_name,
            messages.c.created_at,
            conversations.c.user_id,
            users.c.email,
            users.c.name.label("user_name"),
        )
        .select_from(
            messages
            .join(conversations, conversations.c.id == messages.c.conversation_id)
            .join(users, users.c.id == conversations.c.user_id)
        )
        .order_by(desc(messages.c.created_at))
        .limit(limit)
    ).mappings().all()

    return [
        {
            "id": r["id"],
            "user_email": r["email"],
            "user_name": r["user_name"],
            "role": r["role"],
            "content": r["content"][:500],
            "tool_name": r["tool_name"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ]


# --- Allowlist Management -----------------------------------------------------

class AllowlistAddRequest(BaseModel):
    email: EmailStr


@router.get("/allowlist")
def admin_list_allowlist(
    token: str = Query(...),
    conn: DbConn = ...,
) -> list[dict[str, Any]]:
    """List all allowed registration emails from DB."""
    _require_admin(token)
    from gridbert.storage.repositories.allowlist_repo import list_allowed_emails

    entries = list_allowed_emails(conn)
    return [
        {
            "id": e["id"],
            "email": e["email"],
            "added_by": e["added_by"],
            "created_at": str(e["created_at"]) if e["created_at"] else None,
        }
        for e in entries
    ]


@router.post("/allowlist")
def admin_add_to_allowlist(
    req: AllowlistAddRequest,
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """Add email to registration allowlist."""
    _require_admin(token)
    from gridbert.storage.repositories.allowlist_repo import add_allowed_email, is_email_allowed

    if is_email_allowed(conn, req.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-Mail bereits in Allowlist",
        )

    entry_id = add_allowed_email(conn, req.email)
    return {"id": entry_id, "email": req.email.lower(), "status": "added"}


@router.delete("/allowlist")
def admin_remove_from_allowlist(
    email: str = Query(...),
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """Remove email from registration allowlist."""
    _require_admin(token)
    from gridbert.storage.repositories.allowlist_repo import remove_allowed_email

    removed = remove_allowed_email(conn, email)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="E-Mail nicht in Allowlist",
        )
    return {"email": email.lower(), "status": "removed"}
