# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConsumptionReading(BaseModel):
    """Ein einzelner 15-Minuten-Messwert."""

    timestamp: datetime
    kwh: float


class SmartMeterData(BaseModel):
    """Aggregierte Smart-Meter-Daten."""

    zaehlpunkt: str
    readings: list[ConsumptionReading] = Field(default_factory=list)
    zeitraum_von: datetime | None = None
    zeitraum_bis: datetime | None = None

    @property
    def total_kwh(self) -> float:
        return sum(r.kwh for r in self.readings)

    @property
    def tage(self) -> int:
        if not self.zeitraum_von or not self.zeitraum_bis:
            return 0
        return (self.zeitraum_bis - self.zeitraum_von).days

    @property
    def jahresverbrauch_kwh(self) -> float:
        """Hochrechnung auf 365 Tage."""
        if self.tage <= 0:
            return 0.0
        return self.total_kwh / self.tage * 365

    @property
    def grundlast_watt(self) -> float:
        """Geschätzte Grundlast aus dem Minimum der 15-min-Werte."""
        if not self.readings:
            return 0.0
        min_kwh = min(r.kwh for r in self.readings)
        return min_kwh * 4 * 1000  # 15-min-Wert → Watt
