"""Tests for gridbert.crypto — Fernet encryption/decryption."""

from __future__ import annotations

import pytest

from gridbert.crypto import decrypt_value, encrypt_value


class TestCrypto:
    def test_roundtrip(self):
        plaintext = "sk-ant-api03-abc123-xyz"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext
        assert decrypt_value(encrypted) == plaintext

    def test_different_ciphertexts(self):
        """Same plaintext produces different ciphertexts (Fernet includes timestamp)."""
        a = encrypt_value("test-key")
        b = encrypt_value("test-key")
        assert a != b
        assert decrypt_value(a) == decrypt_value(b) == "test-key"

    def test_empty_string(self):
        encrypted = encrypt_value("")
        assert decrypt_value(encrypted) == ""

    def test_unicode(self):
        plaintext = "Schlüssel-mit-Ümläuten-öäü"
        assert decrypt_value(encrypt_value(plaintext)) == plaintext

    def test_tampered_ciphertext(self):
        encrypted = encrypt_value("original")
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(Exception):
            decrypt_value(tampered)

    def test_invalid_ciphertext(self):
        with pytest.raises(Exception):
            decrypt_value("not-a-valid-token")
