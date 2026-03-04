# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für PV / Balkonkraftwerk Simulation."""

from __future__ import annotations

from pydantic import BaseModel, computed_field


class PVSimulation(BaseModel):
    """Ergebnis einer PV-Simulation."""

    anlage_kwp: float
    ausrichtung: str  # "Süd", "Ost", "West", etc.
    neigung_grad: int = 35
    jahresertrag_kwh: float = 0.0
    eigenverbrauch_kwh: float = 0.0
    eigenverbrauch_anteil_pct: float = 0.0
    einspeisung_kwh: float = 0.0
    einspeiseverguetung_ct: float = 0.0  # OeMAG
    ersparnis_jahr_eur: float = 0.0
    investition_eur: float = 0.0
    foerderung_eur: float = 0.0

    @computed_field
    @property
    def amortisation_jahre(self) -> float:
        """Amortisationsdauer in Jahren."""
        netto_invest = self.investition_eur - self.foerderung_eur
        if self.ersparnis_jahr_eur <= 0 or netto_invest <= 0:
            return 99.0
        return round(netto_invest / self.ersparnis_jahr_eur, 1)

    empfehlung: str = ""
    plz: str = ""
