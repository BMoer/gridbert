# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für Battery Simulation."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class BatteryScenario(BaseModel):
    """Ein Batterie-Szenario mit Ergebnis."""

    kapazitaet_kwh: float
    leistung_kw: float
    preis_eur: float
    eigenverbrauch_erhoehung_kwh: float = 0.0
    ersparnis_jahr_eur: float = 0.0

    @computed_field
    @property
    def amortisation_jahre(self) -> float:
        """Amortisationsdauer in Jahren."""
        if self.ersparnis_jahr_eur <= 0:
            return 99.0
        return round(self.preis_eur / self.ersparnis_jahr_eur, 1)


class BatterySimulation(BaseModel):
    """Gesamtergebnis einer Batterie-Simulation."""

    szenarien: list[BatteryScenario] = Field(default_factory=list)
    bestes_szenario: BatteryScenario | None = None
    empfehlung: str = ""
    grundlast_kw: float = 0.0
    spitzenlast_kw: float = 0.0
    jahresverbrauch_kwh: float = 0.0
