# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from pydantic import BaseModel, Field


class BEGCalculation(BaseModel):
    """Berechnung des Vorteils einer Bürgerenergiegemeinschaft."""

    beg_name: str = Field(default="", description="Name der BEG")
    beg_url: str = Field(default="", description="Website der BEG")
    beg_preis_ct_kwh: float = Field(default=15.15, description="BEG Energiepreis inkl. MwSt")
    versorgungsanteil: float = Field(default=0.5, description="Anteil BEG-Strom (0-1)")
    einmalkosten_eur: float = Field(default=100.0, description="Verrechnungskonto")
    notiz: str = Field(default="", description="Hinweise zum Anbieter")
    jahresverbrauch_kwh: float = 0.0
    aktueller_preis_ct_kwh: float = 0.0

    @property
    def beg_anteil_kwh(self) -> float:
        return self.jahresverbrauch_kwh * self.versorgungsanteil

    @property
    def rest_anteil_kwh(self) -> float:
        return self.jahresverbrauch_kwh * (1 - self.versorgungsanteil)

    @property
    def kosten_mit_beg_eur(self) -> float:
        """Jährliche Energiekosten mit BEG (nur Energieanteil, ohne Grundgebühr)."""
        beg_kosten = self.beg_anteil_kwh * self.beg_preis_ct_kwh / 100
        rest_kosten = self.rest_anteil_kwh * self.aktueller_preis_ct_kwh / 100
        return beg_kosten + rest_kosten

    @property
    def kosten_ohne_beg_eur(self) -> float:
        """Jährliche Energiekosten ohne BEG."""
        return self.jahresverbrauch_kwh * self.aktueller_preis_ct_kwh / 100

    @property
    def ersparnis_jahr_eur(self) -> float:
        return self.kosten_ohne_beg_eur - self.kosten_mit_beg_eur

    @property
    def amortisation_monate(self) -> float:
        if self.ersparnis_jahr_eur <= 0:
            return float("inf")
        return self.einmalkosten_eur / (self.ersparnis_jahr_eur / 12)


class BEGComparison(BaseModel):
    """Vergleich mehrerer BEG-Anbieter."""

    optionen: list[BEGCalculation] = Field(default_factory=list)

    @property
    def beste_beg(self) -> BEGCalculation | None:
        profitable = [b for b in self.optionen if b.ersparnis_jahr_eur > 0]
        if not profitable:
            return None
        return max(profitable, key=lambda b: b.ersparnis_jahr_eur)

    @property
    def max_ersparnis_eur(self) -> float:
        best = self.beste_beg
        return best.ersparnis_jahr_eur if best else 0.0
