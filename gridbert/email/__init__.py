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


def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email via Resend.

    Returns True on success, False on any failure.
    Never raises — email failures must not break core API flows.
    """
    if not RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return False

    try:
        resp = httpx.post(
            _RESEND_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code >= 400:
            log.error("Resend API error %s: %s", resp.status_code, resp.text)
            return False
        log.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        log.exception("Failed to send email to %s", to)
        return False
