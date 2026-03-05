# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""LLM Provider abstraction — Protocol + factory."""

from __future__ import annotations

from typing import Any, Protocol

from gridbert.llm.types import LLMResponse


class LLMProvider(Protocol):
    """Protocol for LLM providers (Claude, OpenAI, etc.)."""

    @property
    def provider_name(self) -> str:
        """Provider identifier: 'claude' or 'openai'."""
        ...

    def chat(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LLMResponse:
        """Send a chat completion request and return a normalized response."""
        ...

    def build_user_content(
        self,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str | list[dict[str, Any]]:
        """Build provider-specific user content with optional attachments."""
        ...

    def build_tool_results_message(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build message(s) containing tool results for the conversation history.

        Claude: single user-role message with tool_result content blocks.
        OpenAI: list of separate tool-role messages.
        """
        ...

    def response_to_history(
        self,
        response: LLMResponse,
    ) -> dict[str, Any]:
        """Convert an LLMResponse to a dict suitable for conversation history."""
        ...


def create_provider(provider_name: str, api_key: str, model: str) -> LLMProvider:
    """Factory: create the right provider instance."""
    if provider_name == "openai":
        from gridbert.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model)

    # Default: Claude
    from gridbert.llm.claude_provider import ClaudeProvider

    return ClaudeProvider(api_key=api_key, model=model)
