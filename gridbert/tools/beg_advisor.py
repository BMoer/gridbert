# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Bürgerenergiegemeinschaft (BEG) — Vergleich mehrerer Anbieter."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from gridbert.models import BEGCalculation, BEGComparison

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROVIDERS_FILE = _DATA_DIR / "beg_providers.json"


def _load_beg_providers() -> list[dict]:
    """BEG-Anbieter-Katalog laden."""
    if not _PROVIDERS_FILE.exists():
        log.warning("BEG-Katalog nicht gefunden: %s", _PROVIDERS_FILE)
        return []
    with open(_PROVIDERS_FILE) as f:
        return json.load(f)


def compare_beg_options(
    jahresverbrauch_kwh: float,
    aktueller_energiepreis_ct_kwh: float,
) -> BEGComparison:
    """Vergleiche alle bekannten BEG-Anbieter für den aktuellen Verbrauch."""
    providers = _load_beg_providers()
    if not providers:
        log.warning("Keine BEG-Anbieter im Katalog")
        return BEGComparison()

    optionen: list[BEGCalculation] = []
    for p in providers:
        calc = BEGCalculation(
            beg_name=p["name"],
            beg_url=p.get("url", ""),
            beg_preis_ct_kwh=p["preis_ct_kwh"],
            versorgungsanteil=p.get("versorgungsanteil", 0.50),
            einmalkosten_eur=p.get("einmalkosten_eur", 0.0),
            notiz=p.get("notiz", ""),
            jahresverbrauch_kwh=jahresverbrauch_kwh,
            aktueller_preis_ct_kwh=aktueller_energiepreis_ct_kwh,
        )
        optionen.append(calc)

    # Sortiere nach Ersparnis (höchste zuerst)
    optionen.sort(key=lambda b: b.ersparnis_jahr_eur, reverse=True)
    return BEGComparison(optionen=optionen)


# Rückwärtskompatibilität
def calculate_beg_advantage(
    jahresverbrauch_kwh: float,
    aktueller_energiepreis_ct_kwh: float,
    versorgungsanteil: float = 0.50,
) -> BEGCalculation:
    """Berechne BEG-Vorteil (Legacy — nutze compare_beg_options())."""
    comparison = compare_beg_options(jahresverbrauch_kwh, aktueller_energiepreis_ct_kwh)
    if comparison.beste_beg:
        return comparison.beste_beg
    # Fallback: 7Energy Defaults
    return BEGCalculation(
        beg_name="7Energy",
        beg_url="https://www.7energy.at",
        jahresverbrauch_kwh=jahresverbrauch_kwh,
        aktueller_preis_ct_kwh=aktueller_energiepreis_ct_kwh,
        versorgungsanteil=versorgungsanteil,
    )


BEITRITTS_SCHRITTE = [
    {
        "schritt": 1,
        "titel": "BEG auswählen",
        "beschreibung": "Vergleiche die Angebote und wähle die passende Energiegemeinschaft.",
        "automatisierbar": False,
    },
    {
        "schritt": 2,
        "titel": "Online beitreten",
        "beschreibung": "Registrierung auf der Website der gewählten BEG — dauert ca. 5 Minuten.",
        "automatisierbar": False,
    },
    {
        "schritt": 3,
        "titel": "Datenfreigabe beim Netzbetreiber",
        "beschreibung": (
            "Im Kundenportal deines Netzbetreibers "
            "die Datenfreigabe für die BEG aktivieren. "
            "Erlaubt den Austausch der Viertelstundenwerte."
        ),
        "automatisierbar": False,
    },
    {
        "schritt": 4,
        "titel": "Zählpunkt anmelden",
        "beschreibung": (
            "Deine Zählpunktnummer bei der BEG hinterlegen. "
            "Die Nummer findest du auf deiner Stromrechnung (beginnt mit AT00...)."
        ),
        "automatisierbar": True,
    },
    {
        "schritt": 5,
        "titel": "Warten auf Zuweisung",
        "beschreibung": (
            "Nach der Anmeldung wirst du einer Erzeugungsanlage zugewiesen. "
            "Das kann einige Wochen dauern. Deinen bisherigen Stromlieferant behältst du "
            "als Reststromlieferant."
        ),
        "automatisierbar": False,
    },
]


def get_beitritts_schritte(zaehlpunkt: str = "", beg_name: str = "") -> list[dict]:
    """Beitrittsschritte zurückgeben, optional mit vorausgefüllten Daten."""
    schritte = [dict(s) for s in BEITRITTS_SCHRITTE]
    if zaehlpunkt:
        for s in schritte:
            if s["schritt"] == 4:
                s["beschreibung"] += f" Deine Nummer: {zaehlpunkt}"
    if beg_name:
        for s in schritte:
            if s["schritt"] == 2:
                s["beschreibung"] = (
                    f"Registrierung bei {beg_name} — dauert ca. 5 Minuten."
                )
    return schritte
