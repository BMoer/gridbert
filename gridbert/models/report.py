# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from gridbert.models.beg import BEGCalculation, BEGComparison
from gridbert.models.invoice import Invoice
from gridbert.models.smart_meter import SmartMeterData
from gridbert.models.tariff import TariffComparison


class ReportSection(str, Enum):
    AKTUELLE_KOSTEN = "aktuelle_kosten"
    TARIFVERGLEICH = "tarifvergleich"
    BEG_VORTEIL = "beg_vorteil"
    GESAMTERSPARNIS = "gesamtersparnis"
    NAECHSTE_SCHRITTE = "naechste_schritte"


class SavingsReport(BaseModel):
    """Der finale Einsparungs-Report."""

    invoice: Invoice
    smart_meter: SmartMeterData | None = None
    tariff_comparison: TariffComparison | None = None
    beg_comparison: BEGComparison | None = None
    beg_calculation: BEGCalculation | None = None

    @property
    def jahresverbrauch_kwh(self) -> float:
        """Bester verfügbarer Wert: Smart Meter > Rechnung."""
        if self.smart_meter and self.smart_meter.jahresverbrauch_kwh > 0:
            return self.smart_meter.jahresverbrauch_kwh
        return self.invoice.jahresverbrauch_kwh

    @property
    def aktuelle_jahreskosten_eur(self) -> float:
        energie = self.jahresverbrauch_kwh * self.invoice.energiepreis_ct_kwh / 100
        grund = self.invoice.grundgebuehr_eur_monat * 12
        return energie + grund

    @property
    def _beste_beg(self) -> BEGCalculation | None:
        """Beste BEG aus Vergleich oder Fallback auf Einzelberechnung."""
        if self.beg_comparison:
            return self.beg_comparison.beste_beg
        return self.beg_calculation

    @property
    def gesamtersparnis_eur(self) -> float:
        ersparnis = 0.0
        if self.tariff_comparison:
            ersparnis += self.tariff_comparison.max_ersparnis_eur
        best_beg = self._beste_beg
        if best_beg:
            ersparnis += best_beg.ersparnis_jahr_eur
        return ersparnis
