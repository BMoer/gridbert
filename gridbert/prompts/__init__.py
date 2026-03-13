# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Modularer System-Prompt — zusammengesetzt aus Domain-Knowledge-Bausteinen."""

from gridbert.prompts.domain import (
    MARKET_RULES,
    PREFERENCE_HANDLING,
    TARIFF_KNOWLEDGE,
    UPCOMING_FEATURES,
)
from gridbert.prompts.journey import USER_JOURNEY
from gridbert.prompts.personality import PERSONALITY, TONALITY
from gridbert.prompts.rules import BEHAVIOR, RULES
from gridbert.prompts.tools import (
    MEMORY_INSTRUCTIONS,
    SUGGESTION_FORMAT,
    WIDGET_INSTRUCTIONS,
)

# v1.0 System Prompt — assembled from modular sections
SYSTEM_PROMPT_V1 = "\n\n".join([
    PERSONALITY,
    TONALITY,
    USER_JOURNEY,
    PREFERENCE_HANDLING,
    TARIFF_KNOWLEDGE,
    MARKET_RULES,
    BEHAVIOR,
    UPCOMING_FEATURES,
    MEMORY_INSTRUCTIONS,
    SUGGESTION_FORMAT,
    WIDGET_INSTRUCTIONS,
    RULES,
])

__all__ = [
    "SYSTEM_PROMPT_V1",
    # Personality
    "PERSONALITY",
    "TONALITY",
    # Journey
    "USER_JOURNEY",
    # Domain
    "PREFERENCE_HANDLING",
    "TARIFF_KNOWLEDGE",
    "MARKET_RULES",
    "UPCOMING_FEATURES",
    # Tools
    "MEMORY_INSTRUCTIONS",
    "WIDGET_INSTRUCTIONS",
    "SUGGESTION_FORMAT",
    # Rules
    "BEHAVIOR",
    "RULES",
]
