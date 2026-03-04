# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Dashboard Routes — Widget-Konfiguration."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from gridbert.api.deps import CurrentUserId, DbConn
from gridbert.storage.schema import dashboard_widgets

router = APIRouter()


class WidgetCreateRequest(BaseModel):
    widget_type: str
    position: int = 0
    config: dict[str, Any] = Field(default_factory=dict)


class WidgetResponse(BaseModel):
    id: int
    widget_type: str
    position: int
    config: dict[str, Any]


@router.get("/widgets", response_model=list[WidgetResponse])
def list_widgets(
    user_id: CurrentUserId,
    conn: DbConn,
) -> list[WidgetResponse]:
    """Alle Dashboard-Widgets eines Users laden."""
    rows = conn.execute(
        select(dashboard_widgets)
        .where(dashboard_widgets.c.user_id == user_id)
        .order_by(dashboard_widgets.c.position)
    ).mappings().all()

    return [
        WidgetResponse(
            id=row["id"],
            widget_type=row["widget_type"],
            position=row["position"],
            config=json.loads(row["config"]) if row["config"] else {},
        )
        for row in rows
    ]


@router.post("/widgets", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
def add_widget(
    req: WidgetCreateRequest,
    user_id: CurrentUserId,
    conn: DbConn,
) -> WidgetResponse:
    """Neues Dashboard-Widget hinzufügen."""
    result = conn.execute(
        dashboard_widgets.insert().values(
            user_id=user_id,
            widget_type=req.widget_type,
            position=req.position,
            config=json.dumps(req.config),
        )
    )
    widget_id = result.inserted_primary_key[0]

    return WidgetResponse(
        id=widget_id,
        widget_type=req.widget_type,
        position=req.position,
        config=req.config,
    )


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_widget(
    widget_id: int,
    user_id: CurrentUserId,
    conn: DbConn,
) -> None:
    """Dashboard-Widget entfernen."""
    result = conn.execute(
        dashboard_widgets.delete().where(
            dashboard_widgets.c.id == widget_id,
            dashboard_widgets.c.user_id == user_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget nicht gefunden",
        )
