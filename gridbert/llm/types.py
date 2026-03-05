# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Shared types for LLM provider abstraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMTextBlock:
    """A text content block from an LLM response."""

    text: str


@dataclass(frozen=True)
class LLMToolUseBlock:
    """A tool-use content block from an LLM response."""

    id: str
    name: str
    input: dict[str, Any]


LLMContentBlock = LLMTextBlock | LLMToolUseBlock


@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response — provider-agnostic.

    stop_reason is normalized to: "end_turn" | "tool_use" | "max_tokens"
    """

    content: tuple[LLMContentBlock, ...] = field(default_factory=tuple)
    stop_reason: str = "end_turn"

    @property
    def text_parts(self) -> list[str]:
        """Extract all text blocks."""
        return [b.text for b in self.content if isinstance(b, LLMTextBlock)]

    @property
    def tool_uses(self) -> list[LLMToolUseBlock]:
        """Extract all tool-use blocks."""
        return [b for b in self.content if isinstance(b, LLMToolUseBlock)]

    @property
    def has_tool_calls(self) -> bool:
        return any(isinstance(b, LLMToolUseBlock) for b in self.content)
