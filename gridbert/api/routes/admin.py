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
from gridbert.storage.schema import (
    analyses,
    conversations,
    dashboard_widgets,
    messages,
    uploaded_files,
    user_memory,
    users,
)

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
    """High-level stats: user count, funnel metrics, per-user details."""
    _require_admin(token)
    import json as _json

    from gridbert.storage.schema import waitlist

    user_count = conn.execute(select(func.count()).select_from(users)).scalar()
    msg_count = conn.execute(select(func.count()).select_from(messages)).scalar()
    conv_count = conn.execute(select(func.count()).select_from(conversations)).scalar()
    waitlist_count = conn.execute(select(func.count()).select_from(waitlist)).scalar()

    # Per-user widget types (invoice_summary / tariff_comparison)
    widget_rows = conn.execute(
        select(
            dashboard_widgets.c.user_id,
            dashboard_widgets.c.widget_type,
            dashboard_widgets.c.config,
        )
    ).all()

    users_with_invoice: set[int] = set()
    users_with_comparison: set[int] = set()
    savings_values: list[float] = []

    for uid, wtype, cfg_raw in widget_rows:
        if wtype == "invoice_summary":
            users_with_invoice.add(uid)
        elif wtype == "tariff_comparison":
            users_with_comparison.add(uid)
            try:
                cfg = _json.loads(cfg_raw) if isinstance(cfg_raw, str) else cfg_raw
                val = cfg.get("savings_eur") or cfg.get("max_ersparnis_eur") or cfg.get("ersparnis_eur")
                if val is not None:
                    savings_values.append(float(val))
            except (ValueError, TypeError, AttributeError):
                continue

    total_savings = round(sum(savings_values), 2) if savings_values else 0

    # Per-user stats
    user_stats = conn.execute(
        select(
            users.c.id,
            users.c.email,
            users.c.name,
            users.c.created_at,
            users.c.nudged_at,
            func.count(messages.c.id).label("message_count"),
        )
        .select_from(
            users
            .outerjoin(conversations, conversations.c.user_id == users.c.id)
            .outerjoin(messages, messages.c.conversation_id == conversations.c.id)
        )
        .group_by(users.c.id)
        .order_by(desc("message_count"))
        .limit(50)
    ).mappings().all()

    return {
        "total_users": user_count,
        "total_waitlist": waitlist_count,
        "total_messages": msg_count,
        "total_conversations": conv_count,
        "users_with_invoice": len(users_with_invoice),
        "users_with_comparison": len(users_with_comparison),
        "total_savings_eur": total_savings,
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "name": u["name"],
                "created_at": str(u["created_at"]) if u["created_at"] else None,
                "nudged_at": str(u["nudged_at"]) if u["nudged_at"] else None,
                "message_count": u["message_count"],
                "has_invoice": u["id"] in users_with_invoice,
                "has_comparison": u["id"] in users_with_comparison,
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

    # Fire-and-forget invitation email
    from gridbert.email import send_email
    from gridbert.email.templates import allowlist_invitation

    subject, html = allowlist_invitation(req.email)
    email_sent = send_email(req.email.lower(), subject, html)

    return {"id": entry_id, "email": req.email.lower(), "status": "added", "email_sent": email_sent}


@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """Delete a user and all associated data (cascading)."""
    _require_admin(token)

    # Verify user exists
    user = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User nicht gefunden",
        )

    # Get conversation IDs for message cleanup
    conv_ids = [
        r["id"]
        for r in conn.execute(
            select(conversations.c.id).where(conversations.c.user_id == user_id)
        ).mappings().all()
    ]

    # Delete in dependency order
    if conv_ids:
        conn.execute(messages.delete().where(messages.c.conversation_id.in_(conv_ids)))
    conn.execute(analyses.delete().where(analyses.c.user_id == user_id))
    conn.execute(dashboard_widgets.delete().where(dashboard_widgets.c.user_id == user_id))
    conn.execute(user_memory.delete().where(user_memory.c.user_id == user_id))
    conn.execute(uploaded_files.delete().where(uploaded_files.c.user_id == user_id))
    conn.execute(conversations.delete().where(conversations.c.user_id == user_id))
    conn.execute(users.delete().where(users.c.id == user_id))
    conn.commit()

    return {"id": user_id, "email": user["email"], "status": "deleted"}


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

    # Also delete the corresponding user account if it exists
    user_deleted = False
    user = conn.execute(
        select(users).where(users.c.email == email.strip().lower())
    ).mappings().first()
    if user:
        user_id = user["id"]
        conv_ids = [
            r["id"]
            for r in conn.execute(
                select(conversations.c.id).where(conversations.c.user_id == user_id)
            ).mappings().all()
        ]
        if conv_ids:
            conn.execute(messages.delete().where(messages.c.conversation_id.in_(conv_ids)))
        conn.execute(analyses.delete().where(analyses.c.user_id == user_id))
        conn.execute(dashboard_widgets.delete().where(dashboard_widgets.c.user_id == user_id))
        conn.execute(user_memory.delete().where(user_memory.c.user_id == user_id))
        conn.execute(uploaded_files.delete().where(uploaded_files.c.user_id == user_id))
        conn.execute(conversations.delete().where(conversations.c.user_id == user_id))
        conn.execute(users.delete().where(users.c.id == user_id))
        conn.commit()
        user_deleted = True

    return {"email": email.lower(), "status": "removed", "user_deleted": user_deleted}


# --- Waitlist -----------------------------------------------------------------

@router.get("/waitlist")
def admin_list_waitlist(
    token: str = Query(...),
    conn: DbConn = ...,
) -> list[dict[str, Any]]:
    """List all waitlist signups."""
    _require_admin(token)
    from gridbert.storage.schema import waitlist

    rows = conn.execute(
        select(waitlist).order_by(desc(waitlist.c.created_at))
    ).mappings().all()
    return [
        {
            "id": r["id"],
            "email": r["email"],
            "name": r["name"],
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ]


# --- Waitlist Import (Screenshot OCR) -----------------------------------------

class WaitlistImportRequest(BaseModel):
    image_data: str  # base64-encoded image (png/jpeg)
    media_type: str = "image/png"


@router.post("/waitlist/import")
def admin_import_waitlist_from_screenshot(
    req: WaitlistImportRequest,
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """Extract emails from a screenshot via Claude Vision, import into waitlist."""
    _require_admin(token)
    import re

    import anthropic

    from gridbert.config import ANTHROPIC_API_KEY
    from gridbert.storage.schema import waitlist

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    # Use Claude Vision to extract emails
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": req.media_type, "data": req.image_data},
                },
                {
                    "type": "text",
                    "text": "Extract ALL email addresses from this screenshot. "
                    "Return ONLY the email addresses, one per line. Nothing else.",
                },
            ],
        }],
    )

    raw_text = response.content[0].text if response.content else ""
    # Extract emails via regex (robust against extra text)
    emails = list({
        m.lower() for m in re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", raw_text)
    })

    if not emails:
        return {"imported": 0, "skipped": 0, "emails": [], "raw": raw_text}

    # Import into waitlist, skip duplicates
    existing = {
        r["email"]
        for r in conn.execute(select(waitlist.c.email)).mappings().all()
    }

    imported = []
    skipped = []
    for email in sorted(emails):
        if email in existing:
            skipped.append(email)
        else:
            conn.execute(waitlist.insert().values(email=email, name=""))
            imported.append(email)
            existing.add(email)

    conn.commit()

    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "imported_emails": imported,
        "skipped_emails": skipped,
    }


# --- Feedback Nudge -----------------------------------------------------------

@router.post("/send-nudge/{user_id}")
def admin_send_nudge_to_user(
    user_id: int,
    token: str = Query(...),
    conn: DbConn = ...,
) -> dict[str, Any]:
    """Send feedback nudge to a specific user and record timestamp."""
    _require_admin(token)
    from datetime import datetime, timezone

    from gridbert.email import send_email
    from gridbert.email.templates import feedback_nudge

    user = conn.execute(select(users).where(users.c.id == user_id)).mappings().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User nicht gefunden")

    subject, html = feedback_nudge(user["name"] or "")
    email_sent = send_email(user["email"], subject, html)

    # Mark as nudged
    now = datetime.now(timezone.utc)
    conn.execute(users.update().where(users.c.id == user_id).values(nudged_at=now))
    conn.commit()

    return {"user_id": user_id, "email": user["email"], "email_sent": email_sent, "nudged_at": str(now)}
