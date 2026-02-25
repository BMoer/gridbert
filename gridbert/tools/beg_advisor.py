# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""7Energy Bürgerenergiegemeinschaft — Kalkulation und Beitritts-Beratung."""

from __future__ import annotations

from gridbert.models import BEGCalculation

# Aktuelle 7Energy BEG Konditionen (Stand 2025)
BEG_PREIS_CT_KWH = 15.15  # inkl. MwSt für Verbraucher
BEG_VERSORGUNGSANTEIL = 0.50  # typisch 30-50%, wir rechnen konservativ mit 50%
BEG_EINMALKOSTEN = 100.0  # Verrechnungskonto

BEITRITTS_SCHRITTE = [
    {
        "schritt": 1,
        "titel": "Vereinsbeitritt",
        "beschreibung": "Online-Registrierung auf 7energy.at — dauert ca. 5 Minuten.",
        "url": "https://www.7energy.at",
        "automatisierbar": False,
    },
    {
        "schritt": 2,
        "titel": "Datenfreigabe beim Netzbetreiber",
        "beschreibung": (
            "Im Kundenportal deines Netzbetreibers (z.B. Wiener Netze) "
            "musst du die Datenfreigabe für 7Energy aktivieren. "
            "Das erlaubt den Austausch der Viertelstundenwerte."
        ),
        "automatisierbar": False,
    },
    {
        "schritt": 3,
        "titel": "Zählpunkt anmelden",
        "beschreibung": (
            "Deine Zählpunktnummer bei 7Energy hinterlegen. "
            "Die Nummer findest du auf deiner Stromrechnung (beginnt mit AT00...)."
        ),
        "automatisierbar": True,
    },
    {
        "schritt": 4,
        "titel": "Bestehenden Stromlieferant beibehalten",
        "beschreibung": (
            "Wichtig: Du behältst deinen bisherigen Stromlieferanten als Reststromlieferant. "
            "Der BEG-Strom deckt nur einen Teil deines Verbrauchs ab (typisch 30-50%)."
        ),
        "automatisierbar": False,
    },
    {
        "schritt": 5,
        "titel": "Warten auf Zuweisung",
        "beschreibung": (
            "Nach der Anmeldung wirst du einer Erzeugungsanlage zugewiesen. "
            "Das kann einige Wochen dauern."
        ),
        "automatisierbar": False,
    },
]


def calculate_beg_advantage(
    jahresverbrauch_kwh: float,
    aktueller_energiepreis_ct_kwh: float,
    versorgungsanteil: float = BEG_VERSORGUNGSANTEIL,
) -> BEGCalculation:
    """Berechne den finanziellen Vorteil eines 7Energy BEG-Beitritts."""
    return BEGCalculation(
        beg_preis_ct_kwh=BEG_PREIS_CT_KWH,
        versorgungsanteil=versorgungsanteil,
        einmalkosten_eur=BEG_EINMALKOSTEN,
        jahresverbrauch_kwh=jahresverbrauch_kwh,
        aktueller_preis_ct_kwh=aktueller_energiepreis_ct_kwh,
    )


def get_beitritts_schritte(zaehlpunkt: str = "") -> list[dict]:
    """Beitrittsschritte zurückgeben, optional mit vorausgefülltem Zählpunkt."""
    schritte = [dict(s) for s in BEITRITTS_SCHRITTE]  # deep copy
    if zaehlpunkt:
        for s in schritte:
            if s["schritt"] == 3:
                s["beschreibung"] += f" Deine Nummer: {zaehlpunkt}"
    return schritte
