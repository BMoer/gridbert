# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Typen für den Agent-Loop: Messages, Events, Tool-Ergebnisse."""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    WIDGET_ADD = "widget_add"
    WIDGET_UPDATE = "widget_update"
    ERROR = "error"
    DONE = "done"


class AgentEvent(BaseModel):
    """Ein Event das vom Agent an das Frontend gestreamt wird."""

    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition eines Tools für die Claude API."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolResult(BaseModel):
    """Ergebnis einer Tool-Ausführung."""

    tool_use_id: str
    content: str
    is_error: bool = False


# Callback-Typ für Event-Streaming an das Frontend
EventCallback = Callable[[AgentEvent], None]
