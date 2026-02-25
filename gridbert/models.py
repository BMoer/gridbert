# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# --- Invoice ----------------------------------------------------------------

class Invoice(BaseModel):
    """Extrahierte Daten aus einer Stromrechnung."""

    lieferant: str = Field(description="Name des Stromlieferanten")
    tarif_name: str = Field(default="", description="Name des Tarifs")
    energiepreis_ct_kwh: float = Field(description="Energiepreis in ct/kWh brutto")
    grundgebuehr_eur_monat: float = Field(default=0.0, description="Grundgebühr in €/Monat brutto")
    jahresverbrauch_kwh: float = Field(description="Jahresverbrauch in kWh")
    plz: str = Field(description="Postleitzahl")
    zaehlpunkt: str = Field(default="", description="Zählpunktnummer (AT00...)")
    netzkosten_eur_jahr: float | None = Field(
        default=None, description="Netzkosten in €/Jahr falls auf Rechnung"
    )


# --- Smart Meter ------------------------------------------------------------

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


# --- Tarife -----------------------------------------------------------------

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


# --- BEG --------------------------------------------------------------------

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


# --- Report -----------------------------------------------------------------

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
    # Rückwärtskompatibilität: einzelne BEGCalculation → beste aus Vergleich
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
