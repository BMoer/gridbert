# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Tarifvergleich via E-Control Tarifkalkulator."""

from __future__ import annotations

import json
import logging
import time

import httpx

from gridbert.models import Tariff, TariffComparison

log = logging.getLogger(__name__)

# E-Control Tarifkalkulator Frontend-API
# Reverse-engineered aus tarifkalkulator.e-control.at
_TARIF_URL = "https://tarifkalkulator.e-control.at/tarifkalkulator/rest"

# Timeout: Connect schnell, Read großzügig (API ist langsam)
_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2  # Sekunden: 2, 4, 8...


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """HTTP-Request mit Retry und exponentiellem Backoff bei transienten Fehlern."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = client.request(method, url, **kwargs)
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Server error {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF_BASE ** (attempt + 1)
                log.warning(
                    "E-Control Anfrage fehlgeschlagen (Versuch %d/%d): %s — warte %ds",
                    attempt + 1, _MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
            else:
                log.error(
                    "E-Control Anfrage endgültig fehlgeschlagen nach %d Versuchen: %s",
                    _MAX_RETRIES, exc,
                )
    raise last_exc  # type: ignore[misc]


def _fetch_tariffs_econtrol(
    plz: str,
    jahresverbrauch_kwh: float,
    smart_meter: bool = True,
) -> list[dict]:
    """Tarife vom E-Control Tarifkalkulator holen (mit Retry)."""
    with httpx.Client(timeout=_TIMEOUT) as client:
        # Step 1: Netzgebiet für PLZ ermitteln
        log.info("Ermittle Netzgebiet für PLZ %s", plz)
        netz_response = _request_with_retry(
            client, "GET", f"{_TARIF_URL}/netzgebiet",
            params={"plz": plz, "sparte": "STROM"},
        )
        netzgebiete = netz_response.json()

        if not netzgebiete:
            raise ValueError(f"Kein Netzgebiet für PLZ {plz} gefunden")

        netzgebiet_id = netzgebiete[0].get("id")

        # Step 2: Tarife abfragen
        log.info(
            "Frage Tarife ab: PLZ=%s, Verbrauch=%d kWh, Netzgebiet=%s",
            plz,
            jahresverbrauch_kwh,
            netzgebiet_id,
        )
        payload = {
            "plz": plz,
            "verbrauch": jahresverbrauch_kwh,
            "sparte": "STROM",
            "netzgebietId": netzgebiet_id,
            "smartMeter": smart_meter,
            "kategorie": "HAUSHALT",
        }
        tarif_response = _request_with_retry(
            client, "POST", f"{_TARIF_URL}/ergebnis",
            json=payload,
        )
        return tarif_response.json()


def _parse_tariff(raw: dict, jahresverbrauch_kwh: float) -> Tariff | None:
    """Einen einzelnen Tarif aus der E-Control Antwort parsen."""
    try:
        lieferant = raw.get("lieferant", {}).get("name", "Unbekannt")
        tarif_name = raw.get("tarifName", raw.get("name", ""))

        # Gesamtkosten pro Jahr (E-Control berechnet das bereits)
        jahreskosten = raw.get("gesamtkosten", 0.0)

        # Energiepreis und Grundgebühr extrahieren
        energiepreis = 0.0
        grundgebuehr_monat = 0.0

        for komponente in raw.get("tarifKomponenten", []):
            typ = komponente.get("typ", "")
            if typ == "ENERGIEPREIS" or "energiepreis" in typ.lower():
                # ct/kWh
                energiepreis = komponente.get("preisBrutto", 0.0)
            elif typ == "GRUNDPAUSCHALE" or "grundp" in typ.lower() or "pauschale" in typ.lower():
                # €/Monat oder €/Jahr
                preis = komponente.get("preisBrutto", 0.0)
                einheit = komponente.get("einheit", "").lower()
                if "jahr" in einheit:
                    grundgebuehr_monat = preis / 12
                else:
                    grundgebuehr_monat = preis

        # Fallback: Berechne aus Jahreskosten wenn nötig
        if jahreskosten == 0 and energiepreis > 0:
            jahreskosten = (
                jahresverbrauch_kwh * energiepreis / 100 + grundgebuehr_monat * 12
            )

        oekostrom = raw.get("oekostrom", False) or raw.get("isOekostrom", False)

        return Tariff(
            lieferant=lieferant,
            tarif_name=tarif_name,
            energiepreis_ct_kwh=energiepreis,
            grundgebuehr_eur_monat=grundgebuehr_monat,
            jahreskosten_eur=jahreskosten,
            ist_oekostrom=oekostrom,
            quelle="e-control",
        )
    except (KeyError, TypeError) as e:
        log.warning("Tarif konnte nicht geparst werden: %s — %s", e, raw)
        return None


def compare_tariffs(
    plz: str,
    jahresverbrauch_kwh: float,
    aktueller_lieferant: str,
    aktueller_energiepreis: float,
    aktuelle_grundgebuehr: float,
    top_n: int = 5,
) -> TariffComparison:
    """Vergleiche aktuellen Tarif gegen E-Control Alternativen."""

    # Aktuellen Tarif als Referenz aufbauen
    aktuelle_jahreskosten = (
        jahresverbrauch_kwh * aktueller_energiepreis / 100
        + aktuelle_grundgebuehr * 12
    )
    aktueller_tarif = Tariff(
        lieferant=aktueller_lieferant,
        tarif_name="Aktueller Tarif",
        energiepreis_ct_kwh=aktueller_energiepreis,
        grundgebuehr_eur_monat=aktuelle_grundgebuehr,
        jahreskosten_eur=aktuelle_jahreskosten,
        quelle="rechnung",
    )

    try:
        raw_tarife = _fetch_tariffs_econtrol(plz, jahresverbrauch_kwh)
    except Exception as e:
        log.error("E-Control Abfrage fehlgeschlagen: %s", e)
        return TariffComparison(
            aktueller_tarif=aktueller_tarif,
            plz=plz,
            jahresverbrauch_kwh=jahresverbrauch_kwh,
        )

    alternativen: list[Tariff] = []
    for raw in raw_tarife:
        tarif = _parse_tariff(raw, jahresverbrauch_kwh)
        if tarif and tarif.jahreskosten_eur > 0:
            alternativen.append(tarif)

    # Sortiere nach Jahreskosten, Top N
    alternativen.sort(key=lambda t: t.jahreskosten_eur)
    alternativen = alternativen[:top_n]

    return TariffComparison(
        aktueller_tarif=aktueller_tarif,
        alternativen=alternativen,
        plz=plz,
        jahresverbrauch_kwh=jahresverbrauch_kwh,
    )
