# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pydantic Models für Load Profile Analysis."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LoadProfileMetrics(BaseModel):
    """Grundlegende Lastprofil-Kennzahlen."""

    mean_kw: float
    median_kw: float
    min_kw: float
    max_kw: float
    std_kw: float
    grundlast_kw: float  # 15th percentile
    spitzenlast_kw: float  # max
    volllaststunden: float  # total_kwh / peak_kw
    grundlast_anteil_pct: float  # base load share
    total_kwh: float
    monthly_kwh: dict[str, float] = Field(default_factory=dict)  # YYYY-MM → kWh
    nacht_mean_kw: float = 0.0  # 22:00-04:00
    wochenende_mean_kw: float = 0.0


class AnomalyResult(BaseModel):
    """Einzelne Anomalie im Lastprofil."""

    datum: date
    wochentag: str
    typ: str  # "shape" | "magnitude" | "both"
    cluster_id: int = 0
    abweichung_kwh: float  # excess vs cluster mean
    spitzen_abweichung_kw: float = 0.0


class ClusterInfo(BaseModel):
    """Information zu einem Lastprofil-Cluster."""

    cluster_id: int
    tage: int
    mean_daily_kwh: float
    typische_wochentage: list[str] = Field(default_factory=list)


class SavingsOpportunity(BaseModel):
    """Einzelne Einsparmöglichkeit."""

    kategorie: str  # base_load, peak_shaving, weekend, night, anomaly
    beschreibung: str
    einsparung_kwh: float
    einsparung_eur: float
    konfidenz: str = "medium"  # high, medium, low


class LoadProfileAnalysis(BaseModel):
    """Gesamtergebnis einer Lastprofil-Analyse."""

    metrics: LoadProfileMetrics
    anomalien: list[AnomalyResult] = Field(default_factory=list)
    cluster: list[ClusterInfo] = Field(default_factory=list)
    einsparpotenziale: list[SavingsOpportunity] = Field(default_factory=list)
    sparpotenzial_kwh: float = 0.0
    sparpotenzial_eur: float = 0.0
    visualisierungen: dict[str, str] = Field(default_factory=dict)  # name → base64 PNG
    analyse_erfolgreich: bool = True
    fehler: str = ""
