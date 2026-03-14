# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Email sending via Resend API — fire-and-forget, never breaks core flows."""

from __future__ import annotations

import logging

import httpx

from gridbert.config import EMAIL_FROM, RESEND_API_KEY

log = logging.getLogger(__name__)

_RESEND_URL = "https://api.resend.com/emails"
_TIMEOUT = 10.0  # seconds


def send_email(
    to: str,
    subject: str,
    html: str,
    *,
    from_addr: str | None = None,
    max_retries: int = 2,
) -> bool:
    """Send a transactional email via Resend.

    Returns True on success, False on any failure.
    Never raises — email failures must not break core API flows.
    """
    import time

    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False

    sender = from_addr or EMAIL_FROM

    for attempt in range(1, max_retries + 2):  # 1 try + max_retries
        try:
            resp = httpx.post(
                _RESEND_URL,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": sender,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
                timeout=_TIMEOUT,
            )
            if resp.status_code == 429 and attempt <= max_retries:
                wait = attempt * 1.0  # 1s, 2s backoff
                log.warning("Resend 429 for %s, retry %d in %ss", to, attempt, wait)
                time.sleep(wait)
                continue
            if resp.status_code >= 400:
                log.error("Resend API error %s: %s", resp.status_code, resp.text)
                return False
            log.info("Email sent to %s: %s", to, subject)
            return True
        except Exception:
            log.exception("Failed to send email to %s", to)
            return False

    return False
