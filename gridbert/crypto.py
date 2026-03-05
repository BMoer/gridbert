# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Symmetric encryption for user secrets (API keys)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from gridbert.config import SECRET_KEY


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible 32-byte key from SECRET_KEY via SHA-256."""
    raw = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(raw)


_fernet = Fernet(_derive_key(SECRET_KEY))


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns URL-safe base64 ciphertext."""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64 ciphertext back to plaintext."""
    return _fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
