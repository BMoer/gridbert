# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""File Repository — Persist and retrieve uploaded files."""

from __future__ import annotations

import base64
import hashlib
import logging
from pathlib import Path

from sqlalchemy import Connection, select

from gridbert.config import UPLOAD_DIR
from gridbert.storage.schema import uploaded_files

log = logging.getLogger(__name__)


def save_file(
    conn: Connection,
    user_id: int,
    file_name: str,
    media_type: str,
    data_b64: str,
) -> dict:
    """Decode base64 data, save to disk, and insert DB row.

    Deduplicates by SHA-256 hash per user — same file content returns existing row.

    Returns:
        Dict with file metadata (id, file_name, media_type, size_bytes, created_at).
    """
    raw = base64.b64decode(data_b64)
    file_hash = hashlib.sha256(raw).hexdigest()

    # Check for existing file with same hash for this user
    existing = conn.execute(
        select(uploaded_files).where(
            uploaded_files.c.user_id == user_id,
            uploaded_files.c.file_hash == file_hash,
        )
    ).first()

    if existing:
        log.info("Dedup: file %s already stored as id=%d", file_name, existing.id)
        return _row_to_dict(existing)

    # Write to disk: UPLOAD_DIR/{user_id}/{hash[:8]}_{file_name}
    user_dir = Path(UPLOAD_DIR) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename (keep only safe chars)
    safe_name = _sanitize_filename(file_name)
    disk_name = f"{file_hash[:8]}_{safe_name}"
    rel_path = f"{user_id}/{disk_name}"
    abs_path = user_dir / disk_name

    abs_path.write_bytes(raw)
    log.info("File saved: %s (%d bytes)", abs_path, len(raw))

    # Insert DB row
    result = conn.execute(
        uploaded_files.insert().values(
            user_id=user_id,
            file_name=file_name,
            media_type=media_type,
            file_hash=file_hash,
            disk_path=rel_path,
            size_bytes=len(raw),
        )
    )

    # Fetch the inserted row
    row = conn.execute(
        select(uploaded_files).where(
            uploaded_files.c.id == result.inserted_primary_key[0],
        )
    ).first()

    return _row_to_dict(row)


def get_user_files(conn: Connection, user_id: int) -> list[dict]:
    """List all files for a user, ordered by most recent first."""
    rows = conn.execute(
        select(uploaded_files)
        .where(uploaded_files.c.user_id == user_id)
        .order_by(uploaded_files.c.created_at.desc())
    ).mappings().all()
    return [dict(r) for r in rows]


def get_file(conn: Connection, user_id: int, file_id: int) -> dict | None:
    """Get single file metadata with ownership check."""
    row = conn.execute(
        select(uploaded_files).where(
            uploaded_files.c.id == file_id,
            uploaded_files.c.user_id == user_id,
        )
    ).first()
    return _row_to_dict(row) if row else None


def read_file_content(
    conn: Connection, user_id: int, file_id: int
) -> tuple[bytes, dict] | None:
    """Read raw bytes from disk + metadata. Returns None if not found or not owned."""
    file_meta = get_file(conn, user_id, file_id)
    if file_meta is None:
        return None

    abs_path = Path(UPLOAD_DIR) / file_meta["disk_path"]
    if not abs_path.exists():
        log.error("File on disk missing: %s", abs_path)
        return None

    return abs_path.read_bytes(), file_meta


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a plain dict."""
    return {
        "id": row.id,
        "file_name": row.file_name,
        "media_type": row.media_type,
        "file_hash": row.file_hash,
        "disk_path": row.disk_path,
        "size_bytes": row.size_bytes,
        "created_at": str(row.created_at) if row.created_at else "",
    }


def _sanitize_filename(name: str) -> str:
    """Keep only safe characters in filename."""
    safe = "".join(
        c if c.isalnum() or c in (".", "-", "_") else "_"
        for c in name
    )
    # Avoid empty or dot-only names
    return safe or "file"
