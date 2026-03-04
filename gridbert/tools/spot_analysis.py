# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Spot Tariff Analysis — Lohnt sich ein Spot-Tarif?

Ported from lastgang-analysator. Key calculations:
- Volume-weighted average: sum(kWh × price) / sum(kWh)
- Time-weighted average: sum(prices) / count(intervals)
- Profile cost factor: (vol_weighted / time_weighted - 1) × 100
- Comparison with fixed tariff
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

import numpy as np

from gridbert.models.spot import MonthlySpotBreakdown, SpotAnalysis

log = logging.getLogger(__name__)

# Typische österreichische Aufschläge (brutto, ct/kWh)
DEFAULT_AUFSCHLAG_CT = 1.5  # Lieferanten-Aufschlag
DEFAULT_NETZ_CT = 3.5  # Netzentgelt
DEFAULT_STEUERN_CT = 2.5  # Steuern & Abgaben
UST_FACTOR = 1.20  # 20% MwSt


def analyze_spot_tariff(
    consumption_data: list[dict],
    spot_prices: list[dict] | None = None,
    fix_preis_ct: float = 20.0,
    aufschlag_ct: float = DEFAULT_AUFSCHLAG_CT,
    netz_ct: float = DEFAULT_NETZ_CT,
    steuern_ct: float = DEFAULT_STEUERN_CT,
) -> SpotAnalysis:
    """Spot-Tarif-Analyse durchführen.

    Args:
        consumption_data: Liste von {timestamp: ISO-string, kwh: float}.
        spot_prices: Liste von {timestamp: ISO-string, price_ct: float (netto ct/kWh)}.
                     Wenn None, wird ENTSO-E API verwendet.
        fix_preis_ct: Vergleichs-Fixpreis (brutto ct/kWh).
        aufschlag_ct: Lieferanten-Aufschlag (netto ct/kWh).
        netz_ct: Netzentgelt (netto ct/kWh).
        steuern_ct: Steuern & Abgaben (netto ct/kWh).

    Returns:
        SpotAnalysis mit Kosten, Profilkostenfaktor und Empfehlung.
    """
    # Spot-Preise laden falls nicht gegeben
    if spot_prices is None:
        spot_prices = _fetch_spot_prices(consumption_data)

    if not spot_prices:
        return SpotAnalysis(
            total_kwh=0, spot_kosten_eur=0, voll_kosten_eur=0,
            avg_spot_volumengewichtet_ct=0, avg_spot_zeitgewichtet_ct=0,
            profilkostenfaktor_pct=0, grundlast_kw=0, grundlast_anteil_pct=0,
            matched_intervals=0,
            empfehlung="Keine Spotpreise verfügbar — Analyse nicht möglich.",
        )

    # Preis-Lookup erstellen (gerundet auf Stunde)
    price_map: dict[str, float] = {}
    for sp in spot_prices:
        ts = datetime.fromisoformat(sp["timestamp"]) if isinstance(sp["timestamp"], str) else sp["timestamp"]
        hour_key = ts.strftime("%Y-%m-%d %H")
        price_map[hour_key] = sp["price_ct"]

    # Matching: Verbrauch × Spotpreis
    total_kwh = 0.0
    spot_cost_ct = 0.0
    full_cost_ct = 0.0
    spot_price_sum = 0.0
    matched = 0
    min_kw = float("inf")

    monthly: dict[str, dict] = defaultdict(lambda: {"kwh": 0.0, "spot_ct": 0.0, "full_ct": 0.0, "prices": []})

    for point in consumption_data:
        ts = datetime.fromisoformat(point["timestamp"]) if isinstance(point["timestamp"], str) else point["timestamp"]
        kwh = point["kwh"]
        kw = kwh / 0.25  # 15-min → kW

        hour_key = ts.strftime("%Y-%m-%d %H")
        spot_price = price_map.get(hour_key)

        if spot_price is None:
            continue

        # Spot-Kosten (netto)
        sc = kwh * spot_price
        # Vollkosten (brutto)
        full_price = (spot_price + aufschlag_ct + netz_ct + steuern_ct) * UST_FACTOR
        fc = kwh * full_price

        spot_cost_ct += sc
        full_cost_ct += fc
        spot_price_sum += spot_price
        total_kwh += kwh
        matched += 1
        min_kw = min(min_kw, kw)

        monat = ts.strftime("%Y-%m")
        monthly[monat]["kwh"] += kwh
        monthly[monat]["spot_ct"] += sc
        monthly[monat]["full_ct"] += fc
        monthly[monat]["prices"].append(spot_price)

    if matched == 0:
        return SpotAnalysis(
            total_kwh=0, spot_kosten_eur=0, voll_kosten_eur=0,
            avg_spot_volumengewichtet_ct=0, avg_spot_zeitgewichtet_ct=0,
            profilkostenfaktor_pct=0, grundlast_kw=0, grundlast_anteil_pct=0,
            matched_intervals=0,
            empfehlung="Keine Datenpunkte konnten Spotpreisen zugeordnet werden.",
        )

    # Durchschnittspreise
    avg_vol = spot_cost_ct / total_kwh  # Volume-weighted
    avg_time = spot_price_sum / matched  # Time-weighted
    profil_faktor = ((avg_vol / avg_time) - 1) * 100 if avg_time > 0 else 0

    # Grundlast
    if min_kw == float("inf"):
        min_kw = 0
    total_hours = matched * 0.25
    grundlast_kwh = min_kw * total_hours
    grundlast_pct = (grundlast_kwh / total_kwh * 100) if total_kwh > 0 else 0

    # Fix-Tarif Vergleich
    fix_kosten_eur = total_kwh * fix_preis_ct / 100

    spot_eur = spot_cost_ct / 100
    voll_eur = full_cost_ct / 100

    # Monatliche Aufschlüsselung
    monthly_breakdown = [
        MonthlySpotBreakdown(
            monat=m,
            verbrauch_kwh=round(d["kwh"], 1),
            spot_kosten_eur=round(d["spot_ct"] / 100, 2),
            voll_kosten_eur=round(d["full_ct"] / 100, 2),
            avg_spot_ct=round(np.mean(d["prices"]), 2) if d["prices"] else 0,
        )
        for m, d in sorted(monthly.items())
    ]

    # Empfehlung
    ersparnis = fix_kosten_eur - voll_eur
    if ersparnis > 50:
        empfehlung = (
            f"Spot-Tarif lohnt sich! Du sparst ca. {ersparnis:.0f} €/Jahr. "
            f"Dein Profilkostenfaktor ({profil_faktor:+.1f}%) zeigt, "
            f"dass du eher in günstigen Stunden verbrauchst."
        )
    elif ersparnis > 0:
        empfehlung = (
            f"Spot-Tarif ist leicht günstiger ({ersparnis:.0f} €/Jahr), "
            f"aber die Ersparnis ist gering. Risiko von Preisschwankungen beachten."
        )
    else:
        empfehlung = (
            f"Fix-Tarif ist günstiger ({-ersparnis:.0f} €/Jahr billiger). "
            f"Dein Verbrauchsprofil (Faktor: {profil_faktor:+.1f}%) passt nicht gut zum Spot-Tarif."
        )

    return SpotAnalysis(
        total_kwh=round(total_kwh, 1),
        spot_kosten_eur=round(spot_eur, 2),
        voll_kosten_eur=round(voll_eur, 2),
        avg_spot_volumengewichtet_ct=round(avg_vol, 2),
        avg_spot_zeitgewichtet_ct=round(avg_time, 2),
        profilkostenfaktor_pct=round(profil_faktor, 2),
        grundlast_kw=round(min_kw, 3),
        grundlast_anteil_pct=round(grundlast_pct, 1),
        matched_intervals=matched,
        monthly_breakdown=monthly_breakdown,
        empfehlung=empfehlung,
        fix_kosten_eur=round(fix_kosten_eur, 2),
        fix_preis_ct=fix_preis_ct,
    )


def _fetch_spot_prices(consumption_data: list[dict]) -> list[dict]:
    """ENTSO-E Day-Ahead Preise für den Zeitraum der Verbrauchsdaten laden."""
    try:
        from entsoe import EntsoePandasClient

        from gridbert.config import ENTSOE_API_KEY

        if not ENTSOE_API_KEY:
            log.warning("ENTSOE_API_KEY nicht konfiguriert")
            return []

        # Zeitraum bestimmen
        timestamps = [datetime.fromisoformat(p["timestamp"]) for p in consumption_data]
        start = min(timestamps)
        end = max(timestamps)

        import pandas as pd
        client = EntsoePandasClient(api_key=ENTSOE_API_KEY)
        prices = client.query_day_ahead_prices(
            "AT",
            start=pd.Timestamp(start, tz="Europe/Vienna"),
            end=pd.Timestamp(end, tz="Europe/Vienna"),
        )

        return [
            {"timestamp": ts.isoformat(), "price_ct": price / 10}  # EUR/MWh → ct/kWh
            for ts, price in prices.items()
        ]
    except ImportError:
        log.info("entsoe-py nicht installiert — keine Spotpreise verfügbar")
        return []
    except Exception as exc:
        log.warning("ENTSO-E API Fehler: %s", exc)
        return []
