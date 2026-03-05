# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Shared file decoding utilities for CSV/Excel files."""

from __future__ import annotations

import io
import logging

log = logging.getLogger(__name__)


def decode_tabular_bytes(raw: bytes, media_type: str, file_name: str) -> str:
    """Decode raw CSV/Excel bytes to text.

    Args:
        raw: Raw file bytes.
        media_type: MIME type (e.g. "text/csv").
        file_name: Original filename (used for format detection and error messages).

    Returns:
        Decoded text content, or [FEHLER: ...] message on failure.
    """
    if len(raw) == 0:
        return f"[FEHLER: Datei {file_name} ist leer (0 Bytes).]"

    try:
        if file_name.endswith((".xlsx", ".xls")) or media_type in (
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ):
            import pandas as pd

            df = pd.read_excel(io.BytesIO(raw))
            text = df.to_csv(index=False)
        else:
            # CSV — try multiple encodings
            for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    text = raw.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw.decode("utf-8", errors="replace")

        # Limit to ~50k chars to avoid blowing up Claude context
        max_chars = 50_000
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... gekürzt, {len(text)} Zeichen gesamt]"

        return text
    except Exception as exc:
        log.exception("Fehler beim Dekodieren von %s", file_name)
        return f"[FEHLER: Datei {file_name} konnte nicht gelesen werden: {exc}]"
