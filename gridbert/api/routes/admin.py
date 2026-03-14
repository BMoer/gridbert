# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Admin Routes — Usage tracking, analytics, allowlist management."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc, func, select

from gridbert.api.deps import JWT_ALGORITHM, DbConn
from gridbert.config import SECRET_KEY
from gridbert.storage.schema import (
    analyses,
    conversations,
    dashboard_widgets,
    messages,
    switching_requests,
    uploaded_files,
    user_memory,
    users,
)

log = logging.getLogger(__name__)

router = APIRouter()

_DASHBOARD_HTML = (
    Path(__file__).resolve().parent.parent / "admin_dashboard.html"
).read_text(encoding="utf-8")


def _verify_admin(
    conn: Any,
    authorization: str | None = None,
) -> int:
    """Verify admin access via JWT Bearer header. Returns admin user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header required")

    jwt_token = authorization[7:]
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        user = conn.execute(
            select(users.c.id, users.c.is_admin).where(users.c.id == user_id)
        ).mappings().first()
        if user and user.get("is_admin"):
            return user_id
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Admin-Zugriff")
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungueltiger Token") from exc


# --- Admin Login --------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def admin_login(req: AdminLoginRequest, conn: DbConn, request: Request) -> dict[str, Any]:
    """Login as admin — returns JWT if user has is_admin flag."""
    from gridbert.api.rate_limit import check_login_rate_limit
    check_login_rate_limit(request.client.host if request.client else "unknown")

    import bcrypt

    from gridbert.config import ACCESS_TOKEN_EXPIRE_MINUTES

    user = conn.execute(
        select(users).where(users.c.email == req.email.lower())
    ).mappings().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-Mail oder Passwort falsch")

    if not bcrypt.checkpw(req.password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-Mail oder Passwort falsch")

    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kein Admin-Zugriff")

    # Record login timestamp
    now = datetime.now(timezone.utc)
    last_login = user.get("admin_last_login_at")
    conn.execute(users.update().where(users.c.id == user["id"]).values(admin_last_login_at=now))
    conn.commit()

    # Create JWT
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": str(user["id"]), "exp": expires}, SECRET_KEY, algorithm=JWT_ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user.get("name", ""),
        "last_login": str(last_login) if last_login else None,
    }


# --- Dashboard HTML -----------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard() -> HTMLResponse:
    """Serve admin dashboard HTML — auth happens in the JS via API calls."""
    return HTMLResponse(_DASHBOARD_HTML)


# --- Analytics ----------------------------------------------------------------

@router.get("/overview")
def admin_overview(
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """High-level stats: user count, funnel metrics, per-user details."""
    _verify_admin(conn, authorization)
    import json as _json

    from gridbert.storage.schema import api_usage, registration_allowlist, waitlist

    user_count = conn.execute(select(func.count()).select_from(users)).scalar()
    msg_count = conn.execute(select(func.count()).select_from(messages)).scalar()
    conv_count = conn.execute(select(func.count()).select_from(conversations)).scalar()
    waitlist_count = conn.execute(select(func.count()).select_from(waitlist)).scalar()
    allowed_count = conn.execute(select(func.count()).select_from(registration_allowlist)).scalar()

    # LLM cost tracking
    total_cost_usd = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.cost_usd), 0.0))
    ).scalar()
    total_input_tokens = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.input_tokens), 0))
    ).scalar()
    total_output_tokens = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.output_tokens), 0))
    ).scalar()
    server_cost_usd = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.cost_usd), 0.0)).where(
            api_usage.c.server_key == 1
        )
    ).scalar()
    user_cost_usd = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.cost_usd), 0.0)).where(
            api_usage.c.server_key == 0
        )
    ).scalar()

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
            users.c.llm_api_key_enc,
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

    # Switching stats
    from gridbert.storage.repositories.switching_repo import get_switching_stats
    switching_stats = get_switching_stats(conn)

    return {
        "total_users": user_count,
        "total_waitlist": waitlist_count,
        "total_allowed": allowed_count,
        "total_messages": msg_count,
        "total_conversations": conv_count,
        "users_with_invoice": len(users_with_invoice),
        "users_with_comparison": len(users_with_comparison),
        "total_savings_eur": total_savings,
        "llm_cost_usd": round(total_cost_usd, 4),
        "llm_server_cost_usd": round(server_cost_usd, 4),
        "llm_user_cost_usd": round(user_cost_usd, 4),
        "llm_input_tokens": total_input_tokens,
        "llm_output_tokens": total_output_tokens,
        "switching": switching_stats,
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
                "uses_own_key": bool(u["llm_api_key_enc"]),
            }
            for u in user_stats
        ],
    }


@router.get("/activity")
def admin_activity(
    conn: DbConn,
    authorization: str | None = Header(None),
    limit: int = Query(50, le=200),
) -> list[dict[str, Any]]:
    """Recent messages across all users (newest first)."""
    _verify_admin(conn, authorization)

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
    conn: DbConn,
    authorization: str | None = Header(None),
) -> list[dict[str, Any]]:
    """List all allowed registration emails from DB."""
    _verify_admin(conn, authorization)
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
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Add email to registration allowlist."""
    _verify_admin(conn, authorization)
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
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Delete a user and all associated data (cascading)."""
    _verify_admin(conn, authorization)

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
    conn.execute(switching_requests.delete().where(switching_requests.c.user_id == user_id))
    conn.execute(dashboard_widgets.delete().where(dashboard_widgets.c.user_id == user_id))
    conn.execute(user_memory.delete().where(user_memory.c.user_id == user_id))
    conn.execute(uploaded_files.delete().where(uploaded_files.c.user_id == user_id))
    conn.execute(conversations.delete().where(conversations.c.user_id == user_id))
    conn.execute(users.delete().where(users.c.id == user_id))
    conn.commit()

    return {"id": user_id, "email": user["email"], "status": "deleted"}


@router.delete("/allowlist")
def admin_remove_from_allowlist(
    conn: DbConn,
    email: str = Query(...),
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Remove email from registration allowlist."""
    _verify_admin(conn, authorization)
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
        conn.execute(switching_requests.delete().where(switching_requests.c.user_id == user_id))
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
    conn: DbConn,
    authorization: str | None = Header(None),
) -> list[dict[str, Any]]:
    """List all waitlist signups with allowlist status."""
    _verify_admin(conn, authorization)
    from gridbert.storage.schema import registration_allowlist, waitlist

    rows = conn.execute(
        select(waitlist).order_by(desc(waitlist.c.created_at))
    ).mappings().all()

    allowed_emails: set[str] = {
        r["email"]
        for r in conn.execute(select(registration_allowlist.c.email)).mappings().all()
    }

    return [
        {
            "id": r["id"],
            "email": r["email"],
            "name": r["name"],
            "is_allowed": r["email"] in allowed_emails,
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        }
        for r in rows
    ]


@router.delete("/waitlist/clear")
def admin_clear_waitlist(
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Delete all waitlist entries."""
    _verify_admin(conn, authorization)
    from gridbert.storage.schema import waitlist

    count = conn.execute(select(func.count()).select_from(waitlist)).scalar()
    conn.execute(waitlist.delete())
    conn.commit()
    return {"deleted": count, "status": "cleared"}


@router.delete("/waitlist/{entry_id}")
def admin_delete_waitlist_entry(
    entry_id: int,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Delete a single waitlist entry."""
    _verify_admin(conn, authorization)
    from gridbert.storage.schema import waitlist

    row = conn.execute(
        select(waitlist).where(waitlist.c.id == entry_id)
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eintrag nicht gefunden")

    conn.execute(waitlist.delete().where(waitlist.c.id == entry_id))
    conn.commit()
    return {"id": entry_id, "email": row["email"], "status": "deleted"}


# --- Waitlist Import (Screenshot OCR) -----------------------------------------

class WaitlistImportRequest(BaseModel):
    image_data: str  # base64-encoded image (png/jpeg)
    media_type: str = "image/png"


@router.post("/waitlist/import")
def admin_import_waitlist_from_screenshot(
    req: WaitlistImportRequest,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Extract emails from a screenshot via Claude Vision, import into waitlist."""
    _verify_admin(conn, authorization)
    import re

    import anthropic

    from gridbert.config import ANTHROPIC_API_KEY
    from gridbert.storage.schema import waitlist

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    # Use Claude Vision to extract emails + dates
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": req.media_type, "data": req.image_data},
                },
                {
                    "type": "text",
                    "text": "Extract ALL email addresses and their dates from this screenshot. "
                    "Return one entry per line in this exact format: EMAIL|DATE\n"
                    "DATE should be in ISO format YYYY-MM-DDTHH:MM (e.g. 2026-03-13T16:06). "
                    "If the year is not visible, assume 2026. "
                    "If no date is visible for an entry, use just the email without |DATE. "
                    "Return ONLY the data lines, nothing else.",
                },
            ],
        }],
    )

    raw_text = response.content[0].text if response.content else ""

    # Parse email|date pairs, fall back to regex for robustness
    from datetime import datetime, timezone

    entries: dict[str, datetime | None] = {}
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Try EMAIL|DATE format
        parts = line.split("|", 1)
        email_match = re.search(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", parts[0],
        )
        if not email_match:
            continue
        email = email_match.group().lower()
        signup_dt: datetime | None = None
        if len(parts) == 2:
            try:
                signup_dt = datetime.fromisoformat(parts[1].strip()).replace(
                    tzinfo=timezone.utc,
                )
            except ValueError:
                pass
        if email not in entries:
            entries[email] = signup_dt

    if not entries:
        return {"imported": 0, "skipped": 0, "emails": [], "raw": raw_text}

    # Import into waitlist, skip duplicates
    existing = {
        r["email"]
        for r in conn.execute(select(waitlist.c.email)).mappings().all()
    }

    imported = []
    skipped = []
    for email in sorted(entries):
        if email in existing:
            skipped.append(email)
        else:
            values: dict[str, Any] = {"email": email, "name": ""}
            if entries[email] is not None:
                values["created_at"] = entries[email]
            conn.execute(waitlist.insert().values(**values))
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
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Send feedback nudge to a specific user and record timestamp."""
    _verify_admin(conn, authorization)
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


# --- AI Summary --------------------------------------------------------------

@router.get("/summary")
def admin_summary(
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """AI-powered activity summary since last admin login."""
    admin_user_id = _verify_admin(conn, authorization)

    from gridbert.storage.schema import api_usage, registration_allowlist, waitlist

    # Determine "since" timestamp
    since = datetime.now(timezone.utc) - timedelta(days=7)  # default: last 7 days
    if admin_user_id:
        admin_user = conn.execute(
            select(users.c.admin_last_login_at).where(users.c.id == admin_user_id)
        ).mappings().first()
        if admin_user and admin_user["admin_last_login_at"]:
            since = admin_user["admin_last_login_at"]
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)

    # Gather activity stats since last login
    new_users = conn.execute(
        select(func.count()).select_from(users).where(users.c.created_at >= since)
    ).scalar() or 0

    new_messages = conn.execute(
        select(func.count()).select_from(messages).where(messages.c.created_at >= since)
    ).scalar() or 0

    new_conversations = conn.execute(
        select(func.count()).select_from(conversations).where(conversations.c.created_at >= since)
    ).scalar() or 0

    new_waitlist = conn.execute(
        select(func.count()).select_from(waitlist).where(waitlist.c.created_at >= since)
    ).scalar() or 0

    # Cost since last login
    cost_since = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.cost_usd), 0.0)).where(
            api_usage.c.created_at >= since
        )
    ).scalar() or 0.0

    # Per-user message counts since last login
    active_users = conn.execute(
        select(
            users.c.email,
            users.c.name,
            func.count(messages.c.id).label("msg_count"),
        )
        .select_from(
            messages
            .join(conversations, conversations.c.id == messages.c.conversation_id)
            .join(users, users.c.id == conversations.c.user_id)
        )
        .where(messages.c.created_at >= since)
        .where(messages.c.role == "user")
        .group_by(users.c.id)
        .order_by(desc("msg_count"))
        .limit(10)
    ).mappings().all()

    active_user_list = [
        {"email": u["email"], "name": u["name"] or "", "messages": u["msg_count"]}
        for u in active_users
    ]

    raw_stats = {
        "since": since.isoformat(),
        "new_users": new_users,
        "new_messages": new_messages,
        "new_conversations": new_conversations,
        "new_waitlist": new_waitlist,
        "cost_usd": round(cost_since, 4),
        "active_users": active_user_list,
    }

    # Generate AI summary using Haiku
    from gridbert.config import ANTHROPIC_API_KEY

    if not ANTHROPIC_API_KEY:
        return {"summary": None, "raw": raw_stats}

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        prompt_data = (
            f"Zeitraum: seit {since.strftime('%d.%m.%Y %H:%M')} UTC\n"
            f"Neue User: {new_users}\n"
            f"Neue Nachrichten: {new_messages}\n"
            f"Neue Conversations: {new_conversations}\n"
            f"Neue Waitlist-Eintraege: {new_waitlist}\n"
            f"LLM-Kosten: ${cost_since:.4f}\n"
            "Aktive User: " + (", ".join(f"{u['email']} ({u['messages']} msgs)" for u in active_user_list) or "keine")
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=(
                "Du bist der Admin-Assistent fuer Gridbert, einen persoenlichen Energie-Agenten. "
                "Fasse die Aktivitaet seit dem letzten Admin-Login zusammen. "
                "Sei knapp (3-5 Saetze). Hebe Anomalien oder bemerkenswerte Dinge hervor "
                "(z.B. ungewoehnlich aktive User, hohe Kosten, keine Aktivitaet). "
                "Antworte auf Deutsch. Verwende keine Emojis. "
                "Beginne NICHT mit einer Ueberschrift oder einem Titel — schreibe direkt den Fliesstext."
            ),
            messages=[{"role": "user", "content": prompt_data}],
        )
        summary_text = response.content[0].text if response.content else None
    except Exception:
        log.exception("AI summary generation failed")
        summary_text = None

    return {"summary": summary_text, "raw": raw_stats}


# --- Weekly Update -----------------------------------------------------------

class WeeklyUpdateRequest(BaseModel):
    days: int = 7
    custom_note: str = ""


class WeeklyUpdateSendRequest(BaseModel):
    subject: str
    body_html: str


@router.post("/weekly-update/generate")
def generate_weekly_update(
    req: WeeklyUpdateRequest,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Generate a weekly update draft (mail + LinkedIn) from commits + activity."""
    _verify_admin(conn, authorization)
    import json as _json
    import time as _time

    import httpx

    from gridbert.config import ANTHROPIC_API_KEY, GITHUB_REPO
    from gridbert.storage.schema import api_usage, waitlist

    # --- Step 1: GitHub commits ---
    commits_list: list[dict[str, str]] = []
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=req.days)).isoformat()
        resp = httpx.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/commits",
            params={"since": since, "per_page": 100},
            timeout=10.0,
        )
        if resp.status_code == 200:
            for c in resp.json():
                commits_list.append({
                    "message": c["commit"]["message"].split("\n")[0],
                    "date": c["commit"]["author"]["date"][:10],
                })
    except Exception:
        log.exception("Failed to fetch GitHub commits")

    # --- Step 2: App activity ---
    since_dt = datetime.now(timezone.utc) - timedelta(days=req.days)

    new_users = conn.execute(
        select(func.count()).select_from(users).where(users.c.created_at >= since_dt)
    ).scalar() or 0

    new_waitlist = conn.execute(
        select(func.count()).select_from(waitlist).where(waitlist.c.created_at >= since_dt)
    ).scalar() or 0

    new_messages = conn.execute(
        select(func.count()).select_from(messages).where(messages.c.created_at >= since_dt)
    ).scalar() or 0

    new_conversations = conn.execute(
        select(func.count()).select_from(conversations).where(conversations.c.created_at >= since_dt)
    ).scalar() or 0

    cost_usd = conn.execute(
        select(func.coalesce(func.sum(api_usage.c.cost_usd), 0.0)).where(
            api_usage.c.created_at >= since_dt
        )
    ).scalar() or 0.0

    # Widget-based stats
    widget_rows = conn.execute(
        select(dashboard_widgets.c.widget_type, dashboard_widgets.c.config)
        .where(dashboard_widgets.c.created_at >= since_dt)
    ).all()

    invoices_count = sum(1 for wt, _ in widget_rows if wt == "invoice_summary")
    comparisons_count = sum(1 for wt, _ in widget_rows if wt == "tariff_comparison")

    savings_total = 0.0
    for wt, cfg_raw in widget_rows:
        if wt != "tariff_comparison":
            continue
        try:
            cfg = _json.loads(cfg_raw) if isinstance(cfg_raw, str) else cfg_raw
            val = cfg.get("savings_eur") or cfg.get("max_ersparnis_eur") or cfg.get("ersparnis_eur")
            if val is not None:
                savings_total += float(val)
        except (ValueError, TypeError, AttributeError):
            continue

    # Recipients count
    total_waitlist = conn.execute(select(func.count()).select_from(waitlist)).scalar() or 0
    total_users = conn.execute(select(func.count()).select_from(users)).scalar() or 0
    recipients_count = total_waitlist + total_users  # dedup happens at send time

    # --- Step 3: LLM generates mail + LinkedIn ---
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    commits_text = "\n".join(f"- {c['date']}: {c['message']}" for c in commits_list) or "Keine Commits in diesem Zeitraum."

    user_message = (
        f"Zeitraum: letzte {req.days} Tage\n\n"
        f"GitHub Commits:\n{commits_text}\n\n"
        f"App Activity:\n"
        f"- Neue User: {new_users}\n"
        f"- Neue Waitlist: {new_waitlist}\n"
        f"- Nachrichten: {new_messages}\n"
        f"- Conversations: {new_conversations}\n"
        f"- LLM-Kosten: ${cost_usd:.2f}\n"
        f"- Rechnungen analysiert: {invoices_count}\n"
        f"- Tarifvergleiche: {comparisons_count}\n"
        f"- Gesamtersparnis identifiziert: {round(savings_total)}€\n"
    )
    if req.custom_note:
        user_message += f"\nBens Notiz: {req.custom_note}"

    system_prompt = (  # noqa: E501
        "Du bist Ben Moerzinger und schreibst dein wöchentliches "
        '"Building Gridbert" Update. '
        "Gridbert ist dein persönliches Lernprojekt — ein Energie-Agent "
        "für österreichische Konsumenten. "
        "Kein Startup, kein Team, kein Funding. Du baust das alleine um "
        "LLM-Agents, den österreichischen Energiemarkt und "
        "strukturiertes Domain-Wissen zu lernen.\n\n"
        "Dein Ton: Direkt, technisch wenn nötig aber verständlich, "
        "persönlich, ehrlich über Rückschläge. "
        'Nicht: Marketing-Sprache, Buzzwords, "excited to announce", '
        "Emoji-Spam.\n"
        "Sprache: Deutsch.\n\n"
        "Generiere zwei Outputs als JSON:\n\n"
        '1. "mail_subject": Betreffzeile für die E-Mail '
        "(kurz, konkret, kein Clickbait)\n"
        '2. "mail_body": HTML-Body für die E-Mail. 3 Abschnitte:\n'
        '   - "Was passiert ist" — konkrete Änderungen der Woche, '
        "aus Commits + Activity abgeleitet. "
        "Keine Commit-Messages copy-pasten, sondern in 2-4 Sätzen "
        "zusammenfassen was sich für User ändert.\n"
        '   - "Was ich gelernt hab" — ein Insight oder eine Erkenntnis '
        "aus der Woche. "
        "Kann technisch sein, kann Markt-bezogen sein.\n"
        '   - "Was als nächstes kommt" — 1-2 konkrete nächste Schritte.\n'
        "   Formatierung: Einfaches HTML, kurze Absätze, "
        "kein Newsletter-Bloat. Max 200 Wörter.\n"
        '3. "linkedin_post": LinkedIn-Post auf Deutsch. '
        "Max 1.300 Zeichen (LinkedIn-Limit vor \"mehr anzeigen\"). "
        "Kein \"Excited to share\". Stattdessen: konkretes Ergebnis "
        "oder Insight als Hook, dann 2-3 Zeilen Kontext, dann Frage "
        "an die Community. Hashtags: "
        "#energiewende #buildinpublic #österreich\n\n"
        "Antworte NUR mit validem JSON, kein Markdown, keine Backticks."
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw_text = response.content[0].text if response.content else "{}"

        # Strip ```json fences if LLM adds them
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = _json.loads(cleaned)
    except (_json.JSONDecodeError, Exception) as exc:
        log.exception("Weekly update LLM call failed")
        raise HTTPException(
            status_code=500,
            detail="LLM-Generierung fehlgeschlagen. Bitte erneut versuchen.",
        ) from exc

    return {
        "mail_subject": result.get("mail_subject", "Building Gridbert — Weekly Update"),
        "mail_body": result.get("mail_body", ""),
        "linkedin_post": result.get("linkedin_post", ""),
        "meta": {
            "commits_count": len(commits_list),
            "period_days": req.days,
            "recipients_count": recipients_count,
        },
    }


@router.post("/weekly-update/send")
def send_weekly_update(
    req: WeeklyUpdateSendRequest,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Send the weekly update email to all waitlist + user recipients."""
    _verify_admin(conn, authorization)
    import time as _time

    from gridbert.email import send_email
    from gridbert.email.templates import weekly_update
    from gridbert.storage.schema import waitlist

    # Collect + deduplicate recipients
    waitlist_emails = {
        r["email"]
        for r in conn.execute(select(waitlist.c.email)).mappings().all()
    }
    user_emails = {
        r["email"]
        for r in conn.execute(select(users.c.email)).mappings().all()
    }
    all_recipients = sorted(waitlist_emails | user_emails)

    if not all_recipients:
        return {"sent": 0, "failed": 0, "errors": []}

    # Wrap in branded template
    html = weekly_update(req.body_html)

    sent = 0
    failed = 0
    errors: list[str] = []

    for email in all_recipients:
        ok = send_email(email, req.subject, html)
        if ok:
            sent += 1
        else:
            failed += 1
            errors.append(email)
        _time.sleep(0.1)  # Resend rate limit

    return {"sent": sent, "failed": failed, "errors": errors}


# --- Switching Queue ----------------------------------------------------------

class SwitchStatusUpdateRequest(BaseModel):
    status: str  # pending | in_progress | completed | cancelled
    notes: str = ""


@router.get("/switches")
def admin_list_switches(
    conn: DbConn,
    authorization: str | None = Header(None),
    status_filter: str | None = Query(None, alias="status"),
) -> dict[str, Any]:
    """List all switching requests with stats."""
    _verify_admin(conn, authorization)
    from gridbert.storage.repositories.switching_repo import (
        get_switching_stats,
        list_all_requests,
    )

    requests = list_all_requests(conn, status_filter=status_filter)
    stats = get_switching_stats(conn)

    return {
        "stats": stats,
        "requests": [
            {
                "id": r["id"],
                "user_id": r["user_id"],
                "user_email": r.get("user_email", ""),
                "user_display_name": r.get("user_display_name", ""),
                "user_name": r["user_name"],
                "user_address": r["user_address"],
                "status": r["status"],
                "current_lieferant": r["current_lieferant"],
                "target_lieferant": r["target_lieferant"],
                "target_tarif": r["target_tarif"],
                "savings_eur": r["savings_eur"],
                "iban": r["iban"],
                "email": r["email"],
                "zaehlpunkt": r["zaehlpunkt"],
                "plz": r["plz"],
                "jahresverbrauch_kwh": r["jahresverbrauch_kwh"],
                "vollmacht_file_id": r["vollmacht_file_id"],
                "notes": r["notes"],
                "created_at": str(r["created_at"]) if r["created_at"] else None,
                "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
            }
            for r in requests
        ],
    }


@router.post("/switches/{request_id}/status")
def admin_update_switch_status(
    request_id: int,
    req: SwitchStatusUpdateRequest,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    """Update switching request status. Sends email on completion."""
    _verify_admin(conn, authorization)
    from gridbert.storage.repositories.switching_repo import (
        get_switching_request,
        update_request_status,
    )

    valid_statuses = {"pending", "in_progress", "completed", "cancelled"}
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Status. Erlaubt: {', '.join(sorted(valid_statuses))}",
        )

    sr = get_switching_request(conn, request_id)
    if not sr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wechselantrag nicht gefunden",
        )

    updated = update_request_status(conn, request_id, req.status, req.notes)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update fehlgeschlagen")

    # Send email on completion
    email_sent = False
    if req.status == "completed":
        from gridbert.email import send_email
        from gridbert.email.templates import switching_completed

        user = conn.execute(
            select(users.c.name, users.c.email).where(users.c.id == sr["user_id"])
        ).mappings().first()
        if user:
            subj, html = switching_completed(
                name=sr["user_name"] or user["name"] or "",
                target_lieferant=sr["target_lieferant"],
                target_tarif=sr["target_tarif"],
                savings_eur=sr["savings_eur"],
            )
            email_sent = send_email(user["email"], subj, html)

            # Update dashboard widget
            existing_widget = conn.execute(
                dashboard_widgets.select().where(
                    dashboard_widgets.c.user_id == sr["user_id"],
                    dashboard_widgets.c.widget_type == "switching_status",
                )
            ).first()
            if existing_widget:
                import json as _json
                cfg = (
                    _json.loads(existing_widget.config)
                    if isinstance(existing_widget.config, str)
                    else existing_widget.config or {}
                )
                cfg["status"] = "completed"
                conn.execute(
                    dashboard_widgets.update()
                    .where(dashboard_widgets.c.id == existing_widget.id)
                    .values(config=_json.dumps(cfg))
                )
                conn.commit()

    return {
        "request_id": request_id,
        "status": req.status,
        "email_sent": email_sent,
    }


@router.get("/switches/{request_id}/vollmacht")
def admin_download_vollmacht(
    request_id: int,
    conn: DbConn,
    authorization: str | None = Header(None),
) -> Any:
    """Download the Vollmacht PDF for a switching request."""
    _verify_admin(conn, authorization)
    from fastapi.responses import FileResponse

    from gridbert.storage.repositories.switching_repo import get_switching_request

    sr = get_switching_request(conn, request_id)
    if not sr or not sr.get("vollmacht_file_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vollmacht nicht gefunden",
        )

    file_row = conn.execute(
        select(uploaded_files.c.disk_path, uploaded_files.c.file_name)
        .where(uploaded_files.c.id == sr["vollmacht_file_id"])
    ).mappings().first()
    if not file_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")

    from gridbert.config import UPLOAD_DIR
    full_path = Path(UPLOAD_DIR) / file_row["disk_path"]
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datei auf Disk nicht gefunden",
        )

    return FileResponse(
        path=str(full_path),
        media_type="application/pdf",
        filename=f"vollmacht_{request_id}.pdf",
    )
