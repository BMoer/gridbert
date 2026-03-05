# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Settings Routes — LLM API key management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from gridbert.api.deps import CurrentUserId, DbConn
from gridbert.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from gridbert.crypto import decrypt_value, encrypt_value
from gridbert.llm import create_provider
from gridbert.storage.repositories.user_repo import get_user_llm_config, set_user_llm_config

log = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_PROVIDERS = ("claude", "openai")


def _default_model(provider: str) -> str:
    if provider == "openai":
        return "gpt-4o"
    return CLAUDE_MODEL


# --- Request / Response Models ------------------------------------------------


class LLMConfigRequest(BaseModel):
    provider: str  # "claude" | "openai"
    api_key: str  # plaintext — encrypted before storage
    model: str = ""  # optional override


class LLMConfigResponse(BaseModel):
    provider: str
    model: str
    has_key: bool  # never expose the actual key


class SetupStatusResponse(BaseModel):
    has_user_key: bool
    has_server_key: bool
    needs_setup: bool
    provider: str


# --- Endpoints ----------------------------------------------------------------


@router.get("/status")
def get_setup_status(
    user_id: CurrentUserId,
    conn: DbConn,
) -> SetupStatusResponse:
    """Check whether the user needs to configure an API key."""
    config = get_user_llm_config(conn, user_id)
    has_user_key = bool(config["api_key_enc"])
    has_server_key = bool(ANTHROPIC_API_KEY)
    return SetupStatusResponse(
        has_user_key=has_user_key,
        has_server_key=has_server_key,
        needs_setup=not has_user_key and not has_server_key,
        provider=config["provider"] or ("claude" if has_server_key else ""),
    )


@router.get("/llm")
def get_llm_config(
    user_id: CurrentUserId,
    conn: DbConn,
) -> LLMConfigResponse:
    """Get current LLM configuration (key is never returned)."""
    config = get_user_llm_config(conn, user_id)
    return LLMConfigResponse(
        provider=config["provider"],
        model=config["model"],
        has_key=bool(config["api_key_enc"]),
    )


@router.put("/llm")
def set_llm_config(
    req: LLMConfigRequest,
    user_id: CurrentUserId,
    conn: DbConn,
) -> LLMConfigResponse:
    """Save LLM configuration. Validates the key before storing."""
    if req.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider muss einer von {SUPPORTED_PROVIDERS} sein",
        )

    if not req.api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-Key darf nicht leer sein",
        )

    model = req.model or _default_model(req.provider)

    # Validate the key by making a minimal API call
    try:
        provider = create_provider(req.provider, req.api_key, model)
        provider.chat(
            system="Reply with exactly: OK",
            messages=[{"role": "user", "content": "test"}],
            tools=[],
            max_tokens=10,
        )
    except Exception as exc:
        log.warning("API key validation failed for user %d: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API-Key ungültig: {exc}",
        )

    encrypted = encrypt_value(req.api_key)
    set_user_llm_config(conn, user_id, req.provider, encrypted, model)
    conn.commit()

    log.info("User %d saved LLM config: provider=%s, model=%s", user_id, req.provider, model)
    return LLMConfigResponse(provider=req.provider, model=model, has_key=True)


@router.delete("/llm")
def delete_llm_config(
    user_id: CurrentUserId,
    conn: DbConn,
) -> dict[str, str]:
    """Remove user's LLM configuration."""
    set_user_llm_config(conn, user_id, "", "", "")
    conn.commit()
    log.info("User %d removed LLM config", user_id)
    return {"status": "removed"}
