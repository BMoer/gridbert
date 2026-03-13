# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Dependency Injection für FastAPI Endpoints."""

from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import Connection

from gridbert.config import SECRET_KEY
from gridbert.storage.database import get_connection as _get_connection
from gridbert.storage.repositories.user_repo import get_user_by_id

_bearer = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


def get_db() -> Generator[Connection, None, None]:
    """DB-Connection als FastAPI Dependency."""
    with _get_connection() as conn:
        yield conn


def _extract_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> int:
    """JWT Token validieren und User-ID extrahieren."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
        ) from exc
    return user_id


def get_current_user_id(
    user_id: Annotated[int, Depends(_extract_user_id)],
    conn: Annotated[Connection, Depends(get_db)],
) -> int:
    """JWT validieren UND prüfen ob User noch in DB existiert."""
    user = get_user_by_id(conn, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User nicht gefunden",
        )
    return user_id


def get_verified_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    conn: Annotated[Connection, Depends(get_db)],
) -> dict:
    """User laden und verifizieren dass er existiert."""
    user = get_user_by_id(conn, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User nicht gefunden",
        )
    return user


# Type aliases für Endpoint-Signaturen
DbConn = Annotated[Connection, Depends(get_db)]
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
CurrentUser = Annotated[dict, Depends(get_verified_user)]
