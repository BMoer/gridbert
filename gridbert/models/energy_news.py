# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für Energy News & Impact Monitor."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EnergyNewsItem(BaseModel):
    """Eine einzelne Energie-Nachricht."""

    titel: str
    zusammenfassung: str
    quelle: str
    url: str = ""
    datum: datetime | None = None
    kategorie: str = ""  # "markt", "geopolitik", "foerderung", "preis"
    relevanz: str = "mittel"  # "hoch", "mittel", "niedrig"
    preis_auswirkung: str = ""  # "steigend", "fallend", "neutral"


class Foerderung(BaseModel):
    """Eine Förderung / Subvention mit Gültigkeits- und Quellendaten."""

    name: str
    beschreibung: str
    betrag_eur: float = 0.0
    betrag_text: str = ""  # z.B. "160 €/kWp"
    bundesland: str = ""  # leer = bundesweit
    zielgruppe: str = ""  # z.B. "Privatpersonen", "Unternehmen"
    kategorie: str = ""  # "pv", "speicher", "heizung", "sanierung", "bkw", "emobil"
    url: str = ""
    quelle: str = ""  # Offizielle Quelle für Verifizierung
    status: str = "aktiv"  # "aktiv", "ausgelaufen", "geplant"
    gueltig_ab: str = ""  # ISO-Datum, z.B. "2025-01-01"
    gueltig_bis: str = ""  # ISO-Datum, z.B. "2026-12-31"
    stand: str = ""  # Datum der letzten Verifizierung, z.B. "2026-03-05"
    voraussetzungen: str = ""  # Kurzbeschreibung der Voraussetzungen
    hinweis: str = ""  # Zusätzliche Hinweise (z.B. "nicht mit Bundesförderung kombinierbar")


class EnergyMonitorResult(BaseModel):
    """Gesamtergebnis des Energy Monitors."""

    nachrichten: list[EnergyNewsItem] = Field(default_factory=list)
    foerderungen: list[Foerderung] = Field(default_factory=list)
    preis_warnung: str = ""  # z.B. "Spotpreise morgen 40% über Durchschnitt"
    zusammenfassung: str = ""  # Personalisierte Zusammenfassung
    katalog_stand: str = ""  # Datum des Förderungskatalogs
