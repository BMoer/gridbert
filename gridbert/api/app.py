# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""FastAPI Application Factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from gridbert.config import CORS_ORIGINS, ENVIRONMENT

import os
SERVE_STATIC = os.getenv("SERVE_STATIC", "true").lower() != "false"
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

    # Security response headers
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            response: Response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # Routes einbinden
    from gridbert.api.routes.auth import router as auth_router
    from gridbert.api.routes.chat import router as chat_router
    from gridbert.api.routes.dashboard import router as dashboard_router
    from gridbert.api.routes.admin import router as admin_router
    from gridbert.api.routes.settings import router as settings_router
    from gridbert.api.routes.waitlist import router as waitlist_router

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(chat_router, prefix="/api", tags=["chat"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(waitlist_router, prefix="/api", tags=["waitlist"])

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # admin.gridbert.at → redirect root to admin dashboard
    from starlette.responses import RedirectResponse

    @app.get("/")
    def root_redirect(request: Request):  # noqa: F811
        if request.headers.get("host", "").startswith("admin."):
            return RedirectResponse(url="/api/admin/dashboard")
        # For non-admin hosts, let static files handle it (or return health)
        return {"status": "ok"}

    # In Produktion: Frontend-Build als statische Dateien servieren
    # (disabled on Fly.io where SERVE_STATIC=false — Vercel serves the frontend)
    if SERVE_STATIC:
        static_dir = Path(__file__).resolve().parent.parent.parent / "static"
        if static_dir.is_dir():
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
            log.info("Serving frontend from %s", static_dir)

    return app
