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
    """Eine Förderung / Subvention."""

    name: str
    beschreibung: str
    betrag_eur: float = 0.0
    betrag_text: str = ""  # z.B. "bis zu 900€"
    bundesland: str = ""  # leer = bundesweit
    zielgruppe: str = ""  # z.B. "Privatpersonen", "Unternehmen"
    url: str = ""
    ablauf_datum: str = ""


class EnergyMonitorResult(BaseModel):
    """Gesamtergebnis des Energy Monitors."""

    nachrichten: list[EnergyNewsItem] = Field(default_factory=list)
    foerderungen: list[Foerderung] = Field(default_factory=list)
    preis_warnung: str = ""  # z.B. "Spotpreise morgen 40% über Durchschnitt"
    zusammenfassung: str = ""  # Personalisierte Zusammenfassung
