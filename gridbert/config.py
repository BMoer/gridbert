# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# --- Environment --------------------------------------------------------------
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

# --- LLM (Claude API) --------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_MAX_TOKENS: int = int(os.getenv("CLAUDE_MAX_TOKENS", "4096"))

# --- Legacy Ollama (for self-hosted / fallback) --------------------------------
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5vl:7b")

# --- Database -----------------------------------------------------------------
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{Path.home() / '.gridbert' / 'gridbert.db'}")

# --- Auth ---------------------------------------------------------------------
SECRET_KEY: str = os.getenv("SECRET_KEY", "gridbert-dev-secret-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24h

# --- CORS (for React frontend) ------------------------------------------------
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# --- Wiener Netze Smart Meter -------------------------------------------------
WIENER_NETZE_EMAIL: str = os.getenv("WIENER_NETZE_EMAIL", "")
WIENER_NETZE_PASSWORD: str = os.getenv("WIENER_NETZE_PASSWORD", "")

# --- File Uploads -------------------------------------------------------------
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(Path.home() / ".gridbert" / "uploads"))

# --- ENTSO-E (spot prices, Phase 3) ------------------------------------------
ENTSOE_API_KEY: str = os.getenv("ENTSOE_API_KEY", "")
