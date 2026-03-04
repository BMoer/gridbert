# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Gas Tariff Comparison — Gas-Tarifvergleich via E-Control API.

Reuses the same E-Control API pattern as tariff_compare.py,
but with energyType=GAS.
"""

from __future__ import annotations

import logging

import httpx

from gridbert.models.gas import GasTariff, GasTariffComparison

log = logging.getLogger(__name__)

# E-Control API (same pattern as electricity)
_API_BASE = "https://www.e-control.at/api/jsonws"
_SESSION_URL = "https://www.e-control.at/konsumenten/gas/gastarife/tarifvergleich"
_TARIFF_API = f"{_API_BASE}/ECGasPortlet_WAR_ECGasportlet/p/auth/gasCalculation"

# Fallback: Portlet-API (neue Variante wie bei Strom)
_PORTLET_API = "https://www.e-control.at/o/ecgas-portlet/api/v1/gas-tariff-calculator"


def compare_gas_tariffs(
    plz: str,
    jahresverbrauch_kwh: float = 15000.0,
    aktueller_tarif: dict | None = None,
) -> GasTariffComparison:
    """Gas-Tarife für eine PLZ vergleichen.

    Args:
        plz: Postleitzahl.
        jahresverbrauch_kwh: Jährlicher Gasverbrauch in kWh.
        aktueller_tarif: Optionaler aktueller Tarif {anbieter, tarif_name, gaspreis_ct_kwh}.

    Returns:
        GasTariffComparison mit Tarifliste und Empfehlung.
    """
    tarife = _fetch_gas_tariffs(plz, jahresverbrauch_kwh)

    current = None
    if aktueller_tarif:
        current = GasTariff(
            anbieter=aktueller_tarif.get("anbieter", ""),
            tarif_name=aktueller_tarif.get("tarif_name", ""),
            gaspreis_ct_kwh=aktueller_tarif.get("gaspreis_ct_kwh", 0),
            grundgebuehr_eur_monat=aktueller_tarif.get("grundgebuehr_eur_monat", 0),
        )

    return GasTariffComparison(
        plz=plz,
        jahresverbrauch_kwh=jahresverbrauch_kwh,
        tarife=tarife,
        aktueller_tarif=current,
    )


def _fetch_gas_tariffs(plz: str, verbrauch_kwh: float) -> list[GasTariff]:
    """Gas-Tarife von E-Control API laden."""
    tarife: list[GasTariff] = []

    try:
        tarife = _try_portlet_api(plz, verbrauch_kwh)
        if tarife:
            return tarife
    except Exception as exc:
        log.warning("Portlet API fehlgeschlagen: %s", exc)

    try:
        tarife = _try_legacy_api(plz, verbrauch_kwh)
    except Exception as exc:
        log.warning("Legacy API fehlgeschlagen: %s", exc)

    return tarife


def _try_portlet_api(plz: str, verbrauch_kwh: float) -> list[GasTariff]:
    """Neue E-Control Portlet API für Gas."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        resp = client.get(
            _PORTLET_API,
            params={
                "plz": plz,
                "verbrauch": int(verbrauch_kwh),
            },
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        return _parse_tariffs(data)


def _try_legacy_api(plz: str, verbrauch_kwh: float) -> list[GasTariff]:
    """Legacy E-Control JSON-WS API für Gas."""
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        # Session-Cookie holen
        client.get(_SESSION_URL)

        resp = client.get(
            _TARIFF_API,
            params={
                "plz": plz,
                "consumptionValue": int(verbrauch_kwh),
            },
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        return _parse_tariffs(data)


def _parse_tariffs(data: dict | list) -> list[GasTariff]:
    """API-Response zu GasTariff-Objekten parsen."""
    tarife: list[GasTariff] = []

    results = data if isinstance(data, list) else data.get("results", data.get("tariffs", []))

    for entry in results:
        try:
            # Preis netto → brutto
            gaspreis_netto = _extract_price(entry)
            gaspreis_brutto = gaspreis_netto * 1.20  # 20% USt

            grundgebuehr_netto = _extract_grundgebuehr(entry)
            grundgebuehr_brutto = grundgebuehr_netto * 1.20

            tarife.append(GasTariff(
                anbieter=entry.get("supplier", entry.get("anbieter", entry.get("lieferant", ""))),
                tarif_name=entry.get("tariffName", entry.get("tarif", entry.get("name", ""))),
                gaspreis_ct_kwh=round(gaspreis_brutto, 2),
                grundgebuehr_eur_monat=round(grundgebuehr_brutto, 2),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            log.debug("Tarif-Parse-Fehler: %s", exc)
            continue

    # Nach Gaspreis sortieren
    tarife.sort(key=lambda t: t.gaspreis_ct_kwh)
    return tarife


def _extract_price(entry: dict) -> float:
    """Gaspreis (netto ct/kWh) aus API-Entry extrahieren."""
    for key in ("energyPrice", "gaspreis", "price", "workingPrice", "arbeitspreis"):
        val = entry.get(key)
        if val is not None:
            return float(val)
    return 0.0


def _extract_grundgebuehr(entry: dict) -> float:
    """Grundgebühr (netto EUR/Monat) aus API-Entry extrahieren."""
    for key in ("basicPrice", "grundgebuehr", "grundpreis", "basePrice"):
        val = entry.get(key)
        if val is not None:
            return float(val)
    return 0.0
