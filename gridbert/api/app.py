# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""FastAPI Application Factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gridbert.config import CORS_ORIGINS, ENVIRONMENT
from gridbert.storage.database import init_db

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / Shutdown."""
    init_db()
    log.info("Gridbert API gestartet (env=%s)", ENVIRONMENT)
    yield


def create_app() -> FastAPI:
    """FastAPI App erstellen und konfigurieren."""
    app = FastAPI(
        title="Gridbert API",
        description="Persönlicher Energie-Agent für österreichische Konsumenten",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if ENVIRONMENT == "development" else None,
        redoc_url=None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes einbinden
    from gridbert.api.routes.auth import router as auth_router
    from gridbert.api.routes.chat import router as chat_router
    from gridbert.api.routes.dashboard import router as dashboard_router

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat_router, prefix="/api", tags=["chat"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # In Produktion: Frontend-Build als statische Dateien servieren
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
        log.info("Serving frontend from %s", static_dir)

    return app
