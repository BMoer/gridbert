# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Generic Tool Registry — reusable, no business-logic dependencies.

This module contains only the ToolRegistry class and ToolDefinition type.
It has no imports from gridbert.config, gridbert.storage, gridbert.prompts,
or any other application-specific module, making it suitable for use as a
standalone library component.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gridbert.agent.types import ToolDefinition

log = logging.getLogger(__name__)


class ToolRegistry:
    """Registry für Agent-Tools.

    Mappt Tool-Namen auf Python-Funktionen und generiert
    Claude API tool definitions.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Registriere ein Tool mit Claude API Definition und Handler."""
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
        )
        self._handlers[name] = handler
        log.debug("Tool registriert: %s", name)

    def definitions(self) -> list[dict[str, Any]]:
        """Claude API tool definitions zurückgeben."""
        return [
            {
                "name": defn.name,
                "description": defn.description,
                "input_schema": defn.input_schema,
            }
            for defn in self._definitions.values()
        ]

    def execute(self, name: str, input_data: dict[str, Any]) -> str:
        """Tool ausführen und Ergebnis als String zurückgeben."""
        handler = self._handlers.get(name)
        if handler is None:
            log.warning("Unbekanntes Tool aufgerufen: %s", name)
            return "Fehler: Unbekanntes Tool aufgerufen."

        log.info("Tool ausführen: %s", name)
        try:
            result = handler(**input_data)
            # Pydantic-Models automatisch serialisieren
            if hasattr(result, "model_dump_json"):
                return result.model_dump_json(indent=2)
            return str(result)
        except Exception as e:
            log.exception("Tool %s fehlgeschlagen: %s", name, e)
            return f"Fehler bei {name}: Das Tool konnte nicht ausgeführt werden."

    def copy_tool(self, name: str, source: ToolRegistry) -> bool:
        """Copy a single tool (definition + handler) from another registry.

        Returns True if the tool was found and copied, False otherwise.
        """
        if name not in source._definitions or name not in source._handlers:
            return False
        self._definitions[name] = source._definitions[name]
        self._handlers[name] = source._handlers[name]
        log.debug("Tool kopiert: %s", name)
        return True

    @property
    def tool_names(self) -> list[str]:
        return list(self._definitions.keys())
