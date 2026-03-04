# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Battery Simulator — Optimale Speichergröße und Amortisation berechnen.

Simulates battery charge/discharge for each 15-minute interval:
- With spot prices: charge when cheap, discharge when expensive
- Without spot prices: peak shaving + self-consumption optimization
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from gridbert.models.battery import BatteryScenario, BatterySimulation

log = logging.getLogger(__name__)

# Standard-Batterie-Szenarien (Marktpreise Stand 2025/2026)
DEFAULT_SCENARIOS = [
    {"kapazitaet_kwh": 2.0, "leistung_kw": 0.8, "preis_eur": 1_200, "name": "Anker SOLIX (2 kWh)"},
    {"kapazitaet_kwh": 5.0, "leistung_kw": 2.5, "preis_eur": 3_500, "name": "Mittelklasse (5 kWh)"},
    {"kapazitaet_kwh": 10.0, "leistung_kw": 5.0, "preis_eur": 6_500, "name": "Hausbatterie (10 kWh)"},
    {"kapazitaet_kwh": 15.0, "leistung_kw": 7.5, "preis_eur": 9_000, "name": "Großspeicher (15 kWh)"},
]

EFFICIENCY = 0.90  # Round-trip efficiency
INTERVAL_H = 0.25  # 15 minutes


def simulate_battery(
    consumption_data: list[dict],
    spot_prices: list[dict] | None = None,
    tarif_preis_ct: float = 20.0,
    szenarien: list[dict] | None = None,
) -> BatterySimulation:
    """Batterie-Simulation für verschiedene Speichergrößen.

    Args:
        consumption_data: Liste von {timestamp: ISO-string, kwh: float}.
        spot_prices: Optionale Spotpreise {timestamp, price_ct}.
        tarif_preis_ct: Aktueller Strompreis (brutto ct/kWh) für Einsparungsrechnung.
        szenarien: Optionale Batterie-Szenarien, sonst DEFAULT_SCENARIOS.

    Returns:
        BatterySimulation mit Szenarien und Empfehlung.
    """
    scenarios = szenarien or DEFAULT_SCENARIOS

    # Verbrauchsdaten vorbereiten
    consumption = np.array([p["kwh"] for p in consumption_data])
    if len(consumption) < 96:
        return BatterySimulation(empfehlung="Zu wenig Daten für eine Simulation.")

    # Spot-Preis-Vektor erstellen (falls vorhanden)
    prices = _build_price_vector(consumption_data, spot_prices)
    has_spot = prices is not None

    results: list[BatteryScenario] = []

    for sc in scenarios:
        cap = sc["kapazitaet_kwh"]
        power = sc["leistung_kw"]
        price = sc["preis_eur"]

        if has_spot:
            savings = _simulate_with_spot(consumption, prices, cap, power)
        else:
            savings = _simulate_peak_shaving(consumption, cap, power, tarif_preis_ct)

        scenario = BatteryScenario(
            kapazitaet_kwh=cap,
            leistung_kw=power,
            preis_eur=price,
            eigenverbrauch_erhoehung_kwh=round(savings["kwh_saved"], 1),
            ersparnis_jahr_eur=round(savings["eur_saved"], 2),
        )
        results.append(scenario)

    # Bestes Szenario nach Amortisation
    viable = [s for s in results if s.ersparnis_jahr_eur > 0]
    best = min(viable, key=lambda s: s.amortisation_jahre) if viable else None

    # Empfehlung
    grundlast_kw = float(np.percentile(consumption / INTERVAL_H, 15))
    spitzenlast_kw = float(np.max(consumption / INTERVAL_H))
    jahresverbrauch = float(np.sum(consumption))

    if best:
        empfehlung = (
            f"Empfehlung: {best.kapazitaet_kwh:.0f} kWh Speicher. "
            f"Ersparnis: {best.ersparnis_jahr_eur:.0f} €/Jahr, "
            f"Amortisation: {best.amortisation_jahre:.1f} Jahre."
        )
    else:
        empfehlung = (
            "Bei deinem Verbrauchsprofil lohnt sich ein Speicher aktuell nicht. "
            "Prüfe erneut wenn du eine PV-Anlage planst."
        )

    return BatterySimulation(
        szenarien=results,
        bestes_szenario=best,
        empfehlung=empfehlung,
        grundlast_kw=round(grundlast_kw, 3),
        spitzenlast_kw=round(spitzenlast_kw, 3),
        jahresverbrauch_kwh=round(jahresverbrauch, 1),
    )


def _simulate_with_spot(
    consumption: np.ndarray,
    prices: np.ndarray,
    capacity_kwh: float,
    max_power_kw: float,
) -> dict:
    """Simulation mit Spot-Preisen: Laden wenn billig, entladen wenn teuer."""
    max_charge_kwh = max_power_kw * INTERVAL_H * EFFICIENCY
    max_discharge_kwh = max_power_kw * INTERVAL_H

    soc = 0.0  # State of charge in kWh
    total_savings_ct = 0.0

    # Median-Preis als Schwelle
    median_price = float(np.median(prices))

    for i in range(len(consumption)):
        price = prices[i]
        load = consumption[i]

        if price < median_price * 0.8:
            # Günstig → Laden
            charge = min(max_charge_kwh, capacity_kwh - soc)
            soc += charge
        elif price > median_price * 1.2 and soc > 0:
            # Teuer → Entladen (Eigenverbrauch decken)
            discharge = min(max_discharge_kwh, soc, load)
            soc -= discharge
            # Ersparnis = entladene Energie × (Teuer-Preis - Durchschnitt)
            total_savings_ct += discharge * (price - median_price)

    # Jahreshochrechnung
    data_days = len(consumption) / 96
    if data_days > 0:
        factor = 365 / data_days
    else:
        factor = 1

    return {
        "kwh_saved": total_savings_ct / (float(np.mean(prices)) or 1) * factor,
        "eur_saved": total_savings_ct / 100 * factor,
    }


def _simulate_peak_shaving(
    consumption: np.ndarray,
    capacity_kwh: float,
    max_power_kw: float,
    tarif_ct: float,
) -> dict:
    """Simulation ohne Spot-Preise: Eigenverbrauchsoptimierung durch Lastglättung."""
    max_charge_kwh = max_power_kw * INTERVAL_H * EFFICIENCY
    max_discharge_kwh = max_power_kw * INTERVAL_H

    soc = 0.0
    kwh_shifted = 0.0

    # Tagesprofil-basierte Strategie
    mean_load = float(np.mean(consumption))

    for i in range(len(consumption)):
        load = consumption[i]

        if load < mean_load * 0.7:
            # Niedriglast → Laden
            charge = min(max_charge_kwh, capacity_kwh - soc)
            soc += charge
        elif load > mean_load * 1.3 and soc > 0:
            # Hochlast → Entladen
            discharge = min(max_discharge_kwh, soc, load - mean_load)
            soc -= discharge
            kwh_shifted += discharge

    # Ersparnis durch bessere Lastverteilung (konservative Schätzung: 5-15% der verschobenen Energie)
    data_days = len(consumption) / 96
    factor = 365 / data_days if data_days > 0 else 1

    kwh_annual = kwh_shifted * factor
    # Ohne Spot: Ersparnis hauptsächlich durch Netzentgelt-Reduktion (~3-5 ct/kWh)
    savings_ct_per_kwh = 4.0  # Konservative Schätzung
    eur_saved = kwh_annual * savings_ct_per_kwh / 100

    return {
        "kwh_saved": kwh_annual,
        "eur_saved": eur_saved,
    }


def _build_price_vector(
    consumption_data: list[dict],
    spot_prices: list[dict] | None,
) -> np.ndarray | None:
    """Spot-Preise auf Verbrauchsdaten-Zeitstempel abbilden."""
    if not spot_prices:
        return None

    price_map: dict[str, float] = {}
    for sp in spot_prices:
        ts = datetime.fromisoformat(sp["timestamp"]) if isinstance(sp["timestamp"], str) else sp["timestamp"]
        price_map[ts.strftime("%Y-%m-%d %H")] = sp["price_ct"]

    prices = []
    for point in consumption_data:
        ts = datetime.fromisoformat(point["timestamp"]) if isinstance(point["timestamp"], str) else point["timestamp"]
        hour_key = ts.strftime("%Y-%m-%d %H")
        price = price_map.get(hour_key)
        if price is None:
            return None  # Incomplete price data
        prices.append(price)

    return np.array(prices)
