# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Waitlist Route — Public signup for the waitlist."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from gridbert.api.deps import DbConn
from gridbert.storage.schema import waitlist

router = APIRouter()


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str = ""


@router.post("/waitlist")
def waitlist_signup(req: WaitlistRequest, conn: DbConn) -> dict[str, Any]:
    """Public endpoint: add email to waitlist and send confirmation."""
    normalized = req.email.strip().lower()

    # Idempotent: if already on waitlist, return success without duplicate error
    existing = conn.execute(
        select(waitlist.c.id).where(waitlist.c.email == normalized).limit(1)
    ).first()
    if existing:
        return {"status": "already_registered", "email": normalized}

    conn.execute(
        waitlist.insert().values(email=normalized, name=req.name.strip())
    )
    conn.commit()

    # Fire-and-forget email
    from gridbert.email import send_email
    from gridbert.email.templates import waitlist_confirmation

    subject, html = waitlist_confirmation(req.name.strip() or None)
    send_email(normalized, subject, html)

    return {"status": "added", "email": normalized}
