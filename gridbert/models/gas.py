# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für Gas-Tarife."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class GasTariff(BaseModel):
    """Ein einzelner Gas-Tarif."""

    anbieter: str
    tarif_name: str
    gaspreis_ct_kwh: float  # brutto
    grundgebuehr_eur_monat: float = 0.0

    def jahreskosten(self, verbrauch_kwh: float) -> float:
        """Jahreskosten berechnen."""
        return (verbrauch_kwh * self.gaspreis_ct_kwh / 100) + (self.grundgebuehr_eur_monat * 12)


class GasTariffComparison(BaseModel):
    """Ergebnis eines Gas-Tarifvergleichs."""

    plz: str
    jahresverbrauch_kwh: float
    tarife: list[GasTariff] = Field(default_factory=list)
    aktueller_tarif: GasTariff | None = None

    @computed_field
    @property
    def bester_tarif(self) -> GasTariff | None:
        """Günstigster Tarif."""
        if not self.tarife:
            return None
        return min(self.tarife, key=lambda t: t.jahreskosten(self.jahresverbrauch_kwh))

    @computed_field
    @property
    def max_ersparnis_eur(self) -> float:
        """Maximale Ersparnis gegenüber aktuellem Tarif."""
        if not self.aktueller_tarif or not self.tarife:
            return 0.0
        aktuelle_kosten = self.aktueller_tarif.jahreskosten(self.jahresverbrauch_kwh)
        best = self.bester_tarif
        if not best:
            return 0.0
        return max(0.0, aktuelle_kosten - best.jahreskosten(self.jahresverbrauch_kwh))
