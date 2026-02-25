# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLite-Persistenz — Profil, Analysen-Verlauf, Einstellungen."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from gridbert.models import SavingsReport

log = logging.getLogger(__name__)

_DEFAULT_DB_DIR = Path.home() / ".gridbert"
_DEFAULT_DB_PATH = _DEFAULT_DB_DIR / "gridbert.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY DEFAULT 1,
    name TEXT DEFAULT '',
    adresse TEXT DEFAULT '',
    plz TEXT DEFAULT '',
    zaehlpunkt TEXT DEFAULT '',
    netzbetreiber TEXT DEFAULT '',
    aktueller_lieferant TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    rechnung_lieferant TEXT,
    rechnung_tarif TEXT,
    energiepreis_ct_kwh REAL,
    grundgebuehr_eur_monat REAL,
    jahresverbrauch_kwh REAL,
    plz TEXT,
    zaehlpunkt TEXT,
    bester_tarif_lieferant TEXT,
    bester_tarif_preis REAL,
    max_ersparnis_eur REAL,
    beste_beg_name TEXT,
    beste_beg_ersparnis REAL,
    netzkosten_eur_jahr REAL,
    report_markdown TEXT,
    raw_json TEXT
);
"""


class GridbertStorage:
    """Lokale SQLite-Datenbank für Gridbert."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        log.debug("Storage geöffnet: %s", self._db_path)

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- Profil ---------------------------------------------------------------

    def get_profile(self) -> dict:
        """Profil laden. Erstellt Defaults wenn keins existiert."""
        row = self._conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
        if row:
            return dict(row)
        now = datetime.now(tz=timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO profile (id, created_at, updated_at) VALUES (1, ?, ?)",
            (now, now),
        )
        self._conn.commit()
        return dict(self._conn.execute("SELECT * FROM profile WHERE id = 1").fetchone())

    def update_profile(self, **fields: str) -> None:
        """Profil-Felder updaten. Nur übergebene Felder werden geändert."""
        allowed = {"name", "adresse", "plz", "zaehlpunkt", "netzbetreiber", "aktueller_lieferant"}
        updates = {k: v for k, v in fields.items() if k in allowed and v}
        if not updates:
            return
        self.get_profile()  # Sicherstellen dass Profil existiert
        updates["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self._conn.execute(
            f"UPDATE profile SET {set_clause} WHERE id = 1",  # noqa: S608
            list(updates.values()),
        )
        self._conn.commit()

    # --- Analysen -------------------------------------------------------------

    def save_analysis(self, report: SavingsReport, markdown: str) -> int:
        """Analyse-Ergebnis speichern. Gibt die neue ID zurück."""
        inv = report.invoice
        tc = report.tariff_comparison
        best_tariff = tc.bester_tarif if tc else None
        best_beg = report._beste_beg

        raw_data = {
            "invoice": inv.model_dump(),
            "tariff_comparison": tc.model_dump() if tc else None,
            "beg_comparison": report.beg_comparison.model_dump() if report.beg_comparison else None,
        }

        cursor = self._conn.execute(
            """INSERT INTO analyses (
                timestamp, rechnung_lieferant, rechnung_tarif,
                energiepreis_ct_kwh, grundgebuehr_eur_monat, jahresverbrauch_kwh,
                plz, zaehlpunkt,
                bester_tarif_lieferant, bester_tarif_preis, max_ersparnis_eur,
                beste_beg_name, beste_beg_ersparnis, netzkosten_eur_jahr,
                report_markdown, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(tz=timezone.utc).isoformat(),
                inv.lieferant,
                inv.tarif_name,
                inv.energiepreis_ct_kwh,
                inv.grundgebuehr_eur_monat,
                report.jahresverbrauch_kwh,
                inv.plz,
                inv.zaehlpunkt,
                best_tariff.lieferant if best_tariff else None,
                best_tariff.jahreskosten_eur if best_tariff else None,
                tc.max_ersparnis_eur if tc else 0.0,
                best_beg.beg_name if best_beg else None,
                best_beg.ersparnis_jahr_eur if best_beg else 0.0,
                tc.netzkosten_eur_jahr if tc else 0.0,
                markdown,
                json.dumps(raw_data, default=str, ensure_ascii=False),
            ),
        )
        self._conn.commit()

        # Profil automatisch aus Rechnungsdaten aktualisieren
        self.update_profile(
            plz=inv.plz,
            zaehlpunkt=inv.zaehlpunkt,
            aktueller_lieferant=inv.lieferant,
            netzbetreiber=tc.netzbetreiber if tc else "",
        )

        analysis_id = cursor.lastrowid
        log.info("Analyse #%d gespeichert", analysis_id)
        return analysis_id  # type: ignore[return-value]

    def get_analyses(self, limit: int = 10) -> list[dict]:
        """Letzte Analysen laden (neueste zuerst)."""
        rows = self._conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_last_analysis(self) -> dict | None:
        """Letzte Analyse laden."""
        analyses = self.get_analyses(limit=1)
        return analyses[0] if analyses else None
