# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# --- Ollama -----------------------------------------------------------------
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:7b")

# --- Wiener Netze Smart Meter -----------------------------------------------
WIENER_NETZE_EMAIL: str = os.getenv("WIENER_NETZE_EMAIL", "")
WIENER_NETZE_PASSWORD: str = os.getenv("WIENER_NETZE_PASSWORD", "")
