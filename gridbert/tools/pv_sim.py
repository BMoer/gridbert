# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""PV / Balkonkraftwerk Simulator — PVGIS API für Ertragsschätzung.

Uses EU JRC PVGIS API (free, no API key needed) for solar yield estimation.
Calculates self-consumption, grid feed-in, and payback period.
"""

from __future__ import annotations

import logging

import httpx

from gridbert.models.pv import PVSimulation

log = logging.getLogger(__name__)

# PLZ → Geokoordinaten (Hauptstädte der Bundesländer + gängige PLZ)
_PLZ_COORDS: dict[str, tuple[float, float]] = {
    "1": (48.21, 16.37),  # Wien
    "2": (47.81, 16.24),  # Niederösterreich
    "3": (48.20, 15.63),  # NÖ West
    "4": (48.30, 14.29),  # Oberösterreich
    "5": (47.80, 13.04),  # Salzburg
    "6": (47.26, 11.39),  # Tirol
    "7": (47.38, 15.09),  # Steiermark (Graz: 8)
    "8": (47.07, 15.44),  # Steiermark
    "9": (46.62, 14.31),  # Kärnten
}

# Typische Ausrichtungen → PVGIS Azimut (0=Süd, -90=Ost, 90=West)
_AUSRICHTUNG_AZIMUT: dict[str, int] = {
    "Süd": 0,
    "Südost": -45,
    "Südwest": 45,
    "Ost": -90,
    "West": 90,
    "Nord": 180,
}

# Typische BKW/PV-Preise (EUR/kWp, Stand 2025/2026)
_PREIS_PRO_KWP: dict[str, float] = {
    "balkonkraftwerk": 600,  # 800W BKW
    "klein": 1400,  # 3-5 kWp Dach
    "mittel": 1200,  # 5-10 kWp
    "gross": 1000,  # >10 kWp
}


def simulate_pv(
    plz: str,
    anlage_kwp: float = 0.8,
    ausrichtung: str = "Süd",
    neigung: int = 35,
    jahresverbrauch_kwh: float = 3200.0,
    strompreis_ct: float = 20.0,
    einspeiseverguetung_ct: float = 0.0,
) -> PVSimulation:
    """PV-Ertrags-Simulation via PVGIS API.

    Args:
        plz: Postleitzahl für Standort.
        anlage_kwp: Anlagengröße in kWp.
        ausrichtung: Ausrichtung (Süd, Ost, West, etc.).
        neigung: Neigungswinkel in Grad.
        jahresverbrauch_kwh: Jährlicher Stromverbrauch.
        strompreis_ct: Aktueller Strompreis (brutto ct/kWh).
        einspeiseverguetung_ct: Einspeisevergütung (ct/kWh), 0 für BKW.

    Returns:
        PVSimulation mit Ertrag, Eigenverbrauch und Amortisation.
    """
    # Koordinaten aus PLZ
    lat, lon = _plz_to_coords(plz)

    # PVGIS API aufrufen
    azimut = _AUSRICHTUNG_AZIMUT.get(ausrichtung, 0)
    jahresertrag = _fetch_pvgis_yield(lat, lon, anlage_kwp, neigung, azimut)

    if jahresertrag <= 0:
        # Fallback: Schätzung basierend auf österreichischem Durchschnitt
        jahresertrag = anlage_kwp * 1050  # ~1050 kWh/kWp in Österreich

    # Eigenverbrauch schätzen
    eigenverbrauch_pct = _estimate_self_consumption(anlage_kwp, jahresverbrauch_kwh)
    eigenverbrauch_kwh = jahresertrag * eigenverbrauch_pct / 100
    einspeisung_kwh = jahresertrag - eigenverbrauch_kwh

    # Ersparnis berechnen
    ersparnis_eigenverbrauch = eigenverbrauch_kwh * strompreis_ct / 100
    erloes_einspeisung = einspeisung_kwh * einspeiseverguetung_ct / 100
    ersparnis_jahr = ersparnis_eigenverbrauch + erloes_einspeisung

    # Investitionskosten
    if anlage_kwp <= 1.0:
        preis_kwp = _PREIS_PRO_KWP["balkonkraftwerk"]
    elif anlage_kwp <= 5.0:
        preis_kwp = _PREIS_PRO_KWP["klein"]
    elif anlage_kwp <= 10.0:
        preis_kwp = _PREIS_PRO_KWP["mittel"]
    else:
        preis_kwp = _PREIS_PRO_KWP["gross"]

    investition = anlage_kwp * preis_kwp

    # Förderung (vereinfacht: österreichische BKW-Förderung)
    foerderung = _estimate_foerderung(anlage_kwp)

    # Empfehlung
    netto_invest = investition - foerderung
    if ersparnis_jahr > 0:
        amort_jahre = netto_invest / ersparnis_jahr
        if amort_jahre < 8:
            empfehlung = f"Klare Empfehlung! Amortisation in {amort_jahre:.1f} Jahren."
        elif amort_jahre < 15:
            empfehlung = f"Lohnt sich langfristig. Amortisation in {amort_jahre:.1f} Jahren."
        else:
            empfehlung = f"Lange Amortisation ({amort_jahre:.1f} Jahre). Prüfe größere Anlage oder Förderungen."
    else:
        empfehlung = "Mit den aktuellen Parametern rechnet sich die Anlage nicht."

    return PVSimulation(
        anlage_kwp=anlage_kwp,
        ausrichtung=ausrichtung,
        neigung_grad=neigung,
        jahresertrag_kwh=round(jahresertrag, 0),
        eigenverbrauch_kwh=round(eigenverbrauch_kwh, 0),
        eigenverbrauch_anteil_pct=round(eigenverbrauch_pct, 1),
        einspeisung_kwh=round(einspeisung_kwh, 0),
        einspeiseverguetung_ct=einspeiseverguetung_ct,
        ersparnis_jahr_eur=round(ersparnis_jahr, 2),
        investition_eur=round(investition, 0),
        foerderung_eur=round(foerderung, 0),
        empfehlung=empfehlung,
        plz=plz,
    )


def _plz_to_coords(plz: str) -> tuple[float, float]:
    """PLZ → lat/lon (vereinfacht über erste Ziffer)."""
    first_digit = plz[0] if plz else "1"
    return _PLZ_COORDS.get(first_digit, (47.5, 14.5))  # Fallback: Mitte Österreich


def _fetch_pvgis_yield(
    lat: float, lon: float, kwp: float, tilt: int, azimuth: int
) -> float:
    """PVGIS API für Jahresertrag aufrufen."""
    try:
        url = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
        params = {
            "lat": lat,
            "lon": lon,
            "peakpower": kwp,
            "loss": 14,  # Systemverluste %
            "angle": tilt,
            "aspect": azimuth,
            "outputformat": "json",
        }
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Jahresertrag aus PVGIS Response
        totals = data.get("outputs", {}).get("totals", {}).get("fixed", {})
        return float(totals.get("E_y", 0))  # kWh/year
    except Exception as exc:
        log.warning("PVGIS API Fehler: %s", exc)
        return 0.0


def _estimate_self_consumption(anlage_kwp: float, verbrauch_kwh: float) -> float:
    """Eigenverbrauchsanteil schätzen (ohne Speicher).

    Basiert auf Erfahrungswerten:
    - BKW (0.6-0.8 kWp): 60-80% Eigenverbrauch
    - Kleine Anlage (3-5 kWp): 25-40%
    - Mittlere Anlage (5-10 kWp): 20-30%
    - Große Anlage (>10 kWp): 15-25%
    """
    ertrag_approx = anlage_kwp * 1050
    ratio = ertrag_approx / verbrauch_kwh if verbrauch_kwh > 0 else 1

    if ratio < 0.3:
        return 75.0  # BKW — fast alles selbst verbraucht
    elif ratio < 0.5:
        return 55.0
    elif ratio < 0.8:
        return 35.0
    elif ratio < 1.2:
        return 25.0
    else:
        return 18.0


def _estimate_foerderung(anlage_kwp: float) -> float:
    """Grobe Förderungsschätzung für Österreich."""
    if anlage_kwp <= 1.0:
        # BKW-Förderung: bis zu 420€ (EAG-Investitionszuschuss)
        return 420.0
    elif anlage_kwp <= 10.0:
        # PV-Förderung: ca. 285 €/kWp (EAG 2025)
        return min(anlage_kwp * 285, 2850)
    else:
        return min(anlage_kwp * 200, 5000)
