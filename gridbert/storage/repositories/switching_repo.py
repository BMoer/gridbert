# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Switching Repository — Tarifwechsel-Anträge verwalten."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import Connection, desc, func, select

from gridbert.storage.schema import switching_requests, users

log = logging.getLogger(__name__)


def create_switching_request(
    conn: Connection,
    *,
    user_id: int,
    target_lieferant: str,
    target_tarif: str,
    savings_eur: float,
    iban: str,
    email: str,
    zaehlpunkt: str = "",
    plz: str = "",
    jahresverbrauch_kwh: float = 0.0,
    current_lieferant: str = "",
    user_name: str = "",
    user_address: str = "",
    vollmacht_file_id: int | None = None,
) -> int:
    """Create a new switching request. Returns the new request ID."""
    result = conn.execute(
        switching_requests.insert().values(
            user_id=user_id,
            status="pending",
            target_lieferant=target_lieferant,
            target_tarif=target_tarif,
            savings_eur=savings_eur,
            iban=iban,
            email=email,
            zaehlpunkt=zaehlpunkt,
            plz=plz,
            jahresverbrauch_kwh=jahresverbrauch_kwh,
            current_lieferant=current_lieferant,
            user_name=user_name,
            user_address=user_address,
            vollmacht_file_id=vollmacht_file_id,
        )
    )
    conn.commit()
    request_id = result.inserted_primary_key[0]
    log.info(
        "Switching request #%d created: %s → %s (%s), savings=%.2f EUR",
        request_id, current_lieferant, target_lieferant, target_tarif, savings_eur,
    )
    return request_id


def get_switching_request(conn: Connection, request_id: int) -> dict | None:
    """Get a single switching request by ID."""
    row = conn.execute(
        select(switching_requests).where(switching_requests.c.id == request_id)
    ).mappings().first()
    return dict(row) if row else None


def get_user_switching_requests(conn: Connection, user_id: int) -> list[dict]:
    """Get all switching requests for a user, newest first."""
    rows = conn.execute(
        select(switching_requests)
        .where(switching_requests.c.user_id == user_id)
        .order_by(desc(switching_requests.c.created_at))
    ).mappings().all()
    return [dict(r) for r in rows]


def list_all_requests(
    conn: Connection,
    status_filter: str | None = None,
) -> list[dict]:
    """List all switching requests with user email, optionally filtered by status."""
    query = (
        select(
            switching_requests,
            users.c.email.label("user_email"),
            users.c.name.label("user_display_name"),
        )
        .select_from(
            switching_requests.join(users, users.c.id == switching_requests.c.user_id)
        )
        .order_by(desc(switching_requests.c.created_at))
    )
    if status_filter:
        query = query.where(switching_requests.c.status == status_filter)

    rows = conn.execute(query).mappings().all()
    return [dict(r) for r in rows]


def update_request_status(
    conn: Connection,
    request_id: int,
    status: str,
    notes: str = "",
) -> bool:
    """Update a switching request's status. Sets completed_at when status is 'completed'."""
    values: dict = {"status": status}
    if notes:
        values["notes"] = notes
    if status == "completed":
        values["completed_at"] = datetime.now(UTC)

    result = conn.execute(
        switching_requests.update()
        .where(switching_requests.c.id == request_id)
        .values(**values)
    )
    conn.commit()
    updated = result.rowcount > 0
    if updated:
        log.info("Switching request #%d → status=%s", request_id, status)
    return updated


def get_switching_stats(conn: Connection) -> dict:
    """Get switching request counts by status."""
    rows = conn.execute(
        select(
            switching_requests.c.status,
            func.count().label("count"),
        ).group_by(switching_requests.c.status)
    ).mappings().all()

    stats = {r["status"]: r["count"] for r in rows}
    stats["total"] = sum(stats.values())
    return stats
