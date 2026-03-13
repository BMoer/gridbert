# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""In-memory sliding-window rate limiter (stdlib only, single instance)."""

from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, status

from gridbert.config import CHAT_RATE_LIMIT

_WINDOW_SECONDS = 60

# key → deque of request timestamps (key can be user_id or IP string)
_requests: dict[str, deque[float]] = {}
_lock = threading.Lock()

# Auth endpoint limits (per IP)
_AUTH_LOGIN_LIMIT = 5  # per minute
_AUTH_REGISTER_LIMIT = 3  # per minute


def _check_limit(key: str, max_requests: int) -> None:
    """Raise 429 if key exceeded max_requests in the last 60s."""
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _lock:
        timestamps = _requests.get(key)

        if timestamps is None:
            timestamps = deque()
            _requests[key] = timestamps

        # Prune old entries
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            wait_seconds = int(timestamps[0] - cutoff) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Zu viele Anfragen. Bitte warte {wait_seconds} Sekunden.",
            )

        timestamps.append(now)


def check_rate_limit(user_id: int) -> None:
    """Raise 429 if user exceeded CHAT_RATE_LIMIT requests in the last 60s."""
    _check_limit(f"chat:{user_id}", CHAT_RATE_LIMIT)


def check_login_rate_limit(client_ip: str) -> None:
    """Raise 429 if IP exceeded login attempts in the last 60s."""
    _check_limit(f"login:{client_ip}", _AUTH_LOGIN_LIMIT)


def check_register_rate_limit(client_ip: str) -> None:
    """Raise 429 if IP exceeded register attempts in the last 60s."""
    _check_limit(f"register:{client_ip}", _AUTH_REGISTER_LIMIT)
