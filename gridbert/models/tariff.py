# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from pydantic import BaseModel, Field


class Tariff(BaseModel):
    """Ein Stromtarif aus dem E-Control Vergleich."""

    lieferant: str
    tarif_name: str
    energiepreis_ct_kwh: float
    grundgebuehr_eur_monat: float
    jahreskosten_eur: float = Field(description="Gesamtkosten €/Jahr inkl. Energie + Grundgebühr")
    ist_oekostrom: bool = False
    quelle: str = Field(default="e-control", description="Datenquelle")


class TariffComparison(BaseModel):
    """Ergebnis des Tarifvergleichs."""

    aktueller_tarif: Tariff
    alternativen: list[Tariff] = Field(default_factory=list)
    plz: str = ""
    jahresverbrauch_kwh: float = 0.0
    netzkosten_eur_jahr: float = Field(default=0.0, description="Behördlich festgelegte Netzkosten €/Jahr brutto")
    netzbetreiber: str = Field(default="", description="Name des Netzbetreibers")

    @property
    def bester_tarif(self) -> Tariff | None:
        if not self.alternativen:
            return None
        return min(self.alternativen, key=lambda t: t.jahreskosten_eur)

    @property
    def max_ersparnis_eur(self) -> float:
        best = self.bester_tarif
        if not best:
            return 0.0
        return self.aktueller_tarif.jahreskosten_eur - best.jahreskosten_eur
