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

# user_id → deque of request timestamps
_requests: dict[int, deque[float]] = {}
_lock = threading.Lock()


def check_rate_limit(user_id: int) -> None:
    """Raise 429 if user exceeded CHAT_RATE_LIMIT requests in the last 60s."""
    now = time.monotonic()
    cutoff = now - _WINDOW_SECONDS

    with _lock:
        timestamps = _requests.get(user_id)

        if timestamps is None:
            timestamps = deque()
            _requests[user_id] = timestamps

        # Prune old entries
        while timestamps and timestamps[0] < cutoff:
            timestamps.popleft()

        # Evict idle users (empty deque)
        if not timestamps and user_id in _requests:
            pass  # will be used below

        if len(timestamps) >= CHAT_RATE_LIMIT:
            wait_seconds = int(timestamps[0] - cutoff) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Zu viele Anfragen. Bitte warte {wait_seconds} Sekunden.",
            )

        timestamps.append(now)
