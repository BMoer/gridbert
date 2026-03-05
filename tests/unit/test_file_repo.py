# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for file persistence — save, dedup, list, read."""

from __future__ import annotations

import base64

import pytest
from sqlalchemy import create_engine, text

from gridbert.storage.schema import metadata


@pytest.fixture
def db_conn(tmp_path, monkeypatch):
    """In-memory SQLite DB with schema + patched UPLOAD_DIR."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr("gridbert.storage.repositories.file_repo.UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr("gridbert.config.UPLOAD_DIR", str(upload_dir))

    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    # Insert a test user
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO users (id, email, password_hash) VALUES (1, 'test@test.at', 'hash')"
        ))
        conn.execute(text(
            "INSERT INTO users (id, email, password_hash) VALUES (2, 'other@test.at', 'hash')"
        ))
        conn.commit()
        yield conn


@pytest.fixture
def csv_b64():
    """Base64-encoded CSV content."""
    csv_text = "timestamp;kWh\n2024-01-01 00:00;0.5\n2024-01-01 00:15;0.6\n"
    return base64.b64encode(csv_text.encode()).decode()


@pytest.fixture
def pdf_b64():
    """Base64-encoded minimal PDF-like content (not a real PDF, for testing storage only)."""
    return base64.b64encode(b"%PDF-1.4 fake content").decode()


class TestSaveFile:
    def test_save_creates_disk_file(self, db_conn, csv_b64, tmp_path):
        from gridbert.storage.repositories.file_repo import save_file

        result = save_file(db_conn, 1, "lastprofil.csv", "text/csv", csv_b64)

        assert result["id"] is not None
        assert result["file_name"] == "lastprofil.csv"
        assert result["media_type"] == "text/csv"
        assert result["size_bytes"] > 0

        # Verify file exists on disk
        disk_path = tmp_path / "uploads" / result["disk_path"]
        assert disk_path.exists()
        assert disk_path.read_bytes() == base64.b64decode(csv_b64)

    def test_save_dedup_same_content(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import save_file

        first = save_file(db_conn, 1, "lastprofil.csv", "text/csv", csv_b64)
        second = save_file(db_conn, 1, "lastprofil_v2.csv", "text/csv", csv_b64)

        # Same file content → same DB row
        assert first["id"] == second["id"]

    def test_save_different_content_creates_new(self, db_conn):
        from gridbert.storage.repositories.file_repo import save_file

        csv1 = base64.b64encode(b"a;b\n1;2").decode()
        csv2 = base64.b64encode(b"x;y\n3;4").decode()

        first = save_file(db_conn, 1, "file1.csv", "text/csv", csv1)
        second = save_file(db_conn, 1, "file2.csv", "text/csv", csv2)

        assert first["id"] != second["id"]

    def test_save_different_users_no_dedup(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import save_file

        user1 = save_file(db_conn, 1, "data.csv", "text/csv", csv_b64)
        user2 = save_file(db_conn, 2, "data.csv", "text/csv", csv_b64)

        # Different users → different rows even with same content
        assert user1["id"] != user2["id"]


class TestGetUserFiles:
    def test_list_returns_user_files(self, db_conn, csv_b64, pdf_b64):
        from gridbert.storage.repositories.file_repo import get_user_files, save_file

        save_file(db_conn, 1, "lastprofil.csv", "text/csv", csv_b64)
        save_file(db_conn, 1, "rechnung.pdf", "application/pdf", pdf_b64)

        files = get_user_files(db_conn, 1)
        names = [f["file_name"] for f in files]

        assert "lastprofil.csv" in names
        assert "rechnung.pdf" in names
        assert len(files) == 2

    def test_list_excludes_other_users(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import get_user_files, save_file

        save_file(db_conn, 1, "mine.csv", "text/csv", csv_b64)
        save_file(db_conn, 2, "theirs.csv", "text/csv",
                  base64.b64encode(b"other data").decode())

        files = get_user_files(db_conn, 1)
        assert len(files) == 1
        assert files[0]["file_name"] == "mine.csv"


class TestGetFile:
    def test_get_file_returns_metadata(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import get_file, save_file

        saved = save_file(db_conn, 1, "data.csv", "text/csv", csv_b64)
        result = get_file(db_conn, 1, saved["id"])

        assert result is not None
        assert result["file_name"] == "data.csv"

    def test_get_file_ownership_check(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import get_file, save_file

        saved = save_file(db_conn, 1, "data.csv", "text/csv", csv_b64)

        # User 2 cannot access User 1's file
        result = get_file(db_conn, 2, saved["id"])
        assert result is None

    def test_get_file_nonexistent(self, db_conn):
        from gridbert.storage.repositories.file_repo import get_file

        result = get_file(db_conn, 1, 99999)
        assert result is None


class TestReadFileContent:
    def test_read_returns_bytes_and_metadata(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import read_file_content, save_file

        saved = save_file(db_conn, 1, "data.csv", "text/csv", csv_b64)
        result = read_file_content(db_conn, 1, saved["id"])

        assert result is not None
        raw_bytes, meta = result
        assert raw_bytes == base64.b64decode(csv_b64)
        assert meta["file_name"] == "data.csv"

    def test_read_ownership_check(self, db_conn, csv_b64):
        from gridbert.storage.repositories.file_repo import read_file_content, save_file

        saved = save_file(db_conn, 1, "data.csv", "text/csv", csv_b64)
        result = read_file_content(db_conn, 2, saved["id"])
        assert result is None


class TestDecodeTabularBytes:
    def test_csv_decode(self):
        from gridbert.tools.file_utils import decode_tabular_bytes

        raw = b"timestamp;kWh\n2024-01-01;0.5\n"
        result = decode_tabular_bytes(raw, "text/csv", "test.csv")

        assert "timestamp" in result
        assert "0.5" in result

    def test_empty_bytes(self):
        from gridbert.tools.file_utils import decode_tabular_bytes

        result = decode_tabular_bytes(b"", "text/csv", "empty.csv")
        assert "FEHLER" in result

    def test_latin1_csv(self):
        from gridbert.tools.file_utils import decode_tabular_bytes

        raw = "Zeitstempel;Verbrauch\n2024-01-01;1.5\nÜberschuss;0.2\n".encode("latin-1")
        result = decode_tabular_bytes(raw, "text/csv", "latin.csv")

        assert "Zeitstempel" in result
        assert "Überschuss" in result or "berschuss" in result

    def test_truncation(self):
        from gridbert.tools.file_utils import decode_tabular_bytes

        raw = ("x" * 60_000).encode()
        result = decode_tabular_bytes(raw, "text/csv", "big.csv")

        assert "gekürzt" in result
        assert len(result) < 60_000


class TestSanitizeFilename:
    def test_normal_name(self):
        from gridbert.storage.repositories.file_repo import _sanitize_filename

        assert _sanitize_filename("lastprofil.csv") == "lastprofil.csv"

    def test_special_chars(self):
        from gridbert.storage.repositories.file_repo import _sanitize_filename

        result = _sanitize_filename("mein lastprofil (1).csv")
        assert " " not in result
        assert "(" not in result
        assert result.endswith(".csv")

    def test_empty_name(self):
        from gridbert.storage.repositories.file_repo import _sanitize_filename

        assert _sanitize_filename("") == "file"
