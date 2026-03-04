# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für Spot Tariff Analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class MonthlySpotBreakdown(BaseModel):
    """Monatliche Spot-Kosten Aufschlüsselung."""

    monat: str  # YYYY-MM
    verbrauch_kwh: float
    spot_kosten_eur: float
    voll_kosten_eur: float  # Spot + Netz + Steuern + USt
    avg_spot_ct: float  # Durchschnittlicher Spotpreis ct/kWh


class SpotAnalysis(BaseModel):
    """Ergebnis einer Spot-Tarif-Analyse."""

    total_kwh: float
    spot_kosten_eur: float  # Reiner Spotpreis
    voll_kosten_eur: float  # Spot + alle Aufschläge
    avg_spot_volumengewichtet_ct: float  # Was User tatsächlich zahlt
    avg_spot_zeitgewichtet_ct: float  # Was Flachprofil zahlen würde
    profilkostenfaktor_pct: float  # Abweichung in %
    grundlast_kw: float
    grundlast_anteil_pct: float
    matched_intervals: int
    monthly_breakdown: list[MonthlySpotBreakdown] = Field(default_factory=list)
    empfehlung: str = ""  # "Spot lohnt sich" / "Fix ist besser"

    # Vergleich mit Fix-Tarif
    fix_kosten_eur: float = 0.0  # Kosten bei Fix-Tarif
    fix_preis_ct: float = 0.0  # Angenommener Fix-Preis ct/kWh

    @computed_field
    @property
    def ersparnis_vs_fix_eur(self) -> float:
        """Ersparnis gegenüber Fix-Tarif (positiv = Spot ist billiger)."""
        if self.fix_kosten_eur <= 0:
            return 0.0
        return self.fix_kosten_eur - self.voll_kosten_eur
