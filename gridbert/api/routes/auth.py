# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Auth Routes — Registrierung und Login mit JWT."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt
from pydantic import BaseModel, EmailStr, Field

from gridbert.api.deps import CurrentUser, DbConn, JWT_ALGORITHM
from gridbert.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY
from gridbert.storage.repositories.user_repo import (
    create_user,
    get_user_by_email,
)

router = APIRouter()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str


class UserProfileResponse(BaseModel):
    id: int
    email: str
    name: str
    plz: str


def _create_token(user_id: int) -> str:
    """JWT Access Token generieren."""
    expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, conn: DbConn, request: Request) -> TokenResponse:
    """Neuen User registrieren."""
    from gridbert.api.rate_limit import check_register_rate_limit
    check_register_rate_limit(request.client.host if request.client else "unknown")

    from gridbert.storage.repositories.allowlist_repo import is_email_allowed, list_allowed_emails

    # Allowlist: DB is the source of truth (env var is seeded into DB on startup).
    # If DB allowlist is empty → open registration. Otherwise, email must be in DB.
    if list_allowed_emails(conn) and not is_email_allowed(conn, req.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registrierung ist derzeit nur auf Einladung möglich. "
                   "Trag dich auf die Warteliste ein: www.gridbert.at",
        )

    existing = get_user_by_email(conn, req.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-Mail bereits registriert",
        )

    password_hash = _hash_password(req.password)
    user_id = create_user(conn, email=req.email, password_hash=password_hash, name=req.name)

    # Auto-promote to admin if email is in ADMIN_EMAILS
    from gridbert.config import ADMIN_EMAILS
    from gridbert.storage.schema import users

    if req.email.lower() in ADMIN_EMAILS:
        conn.execute(users.update().where(users.c.id == user_id).values(is_admin=1))
        conn.commit()

    token = _create_token(user_id)

    # Fire-and-forget welcome email
    from gridbert.email import send_email
    from gridbert.email.templates import welcome_after_registration

    subject, html = welcome_after_registration(req.name)
    send_email(req.email, subject, html)

    return TokenResponse(
        access_token=token,
        user_id=user_id,
        name=req.name,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, conn: DbConn, request: Request) -> TokenResponse:
    """Login mit E-Mail und Passwort."""
    from gridbert.api.rate_limit import check_login_rate_limit
    check_login_rate_limit(request.client.host if request.client else "unknown")
    user = get_user_by_email(conn, req.email)
    if user is None or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-Mail oder Passwort falsch",
        )

    token = _create_token(user["id"])

    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        name=user.get("name", ""),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_profile(user: CurrentUser) -> UserProfileResponse:
    """Aktuelles User-Profil laden."""
    return UserProfileResponse(
        id=user["id"],
        email=user["email"],
        name=user.get("name", ""),
        plz=user.get("plz", ""),
    )
