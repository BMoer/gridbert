# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Energy News & Impact Monitor — Nachrichten, Preise, Förderungen.

Three pillars:
1. Geopolitics & Markets — RSS feeds + Claude summarization
2. Spot & Wholesale Prices — ENTSO-E price alerts
3. Förderungen & Subsidies — Curated catalog filtered by user profile
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

from gridbert.models.energy_news import (
    EnergyMonitorResult,
    EnergyNewsItem,
    Foerderung,
)

log = logging.getLogger(__name__)

# RSS Feeds für Energie-News
_RSS_FEEDS = [
    {
        "url": "https://www.orf.at/stories/rss/orf-stories.xml",
        "name": "ORF",
        "kategorie": "allgemein",
    },
    {
        "url": "https://oesterreichsenergie.at/rss.xml",
        "name": "Oesterreichs Energie",
        "kategorie": "markt",
    },
]

# Energie-relevante Schlüsselwörter
_ENERGY_KEYWORDS = [
    "strom", "gas", "energie", "tarif", "preis", "solar", "photovoltaik",
    "windkraft", "netz", "blackout", "kraftwerk", "erneuerbar", "fossil",
    "opec", "pipeline", "russland", "iran", "saudi", "lng", "öl",
    "co2", "klima", "förderung", "subvention", "wärmepumpe", "heizung",
    "elektrizität", "kwh", "megawatt", "gigawatt", "spot", "börse",
    "ukraine", "sanktion", "embargo", "nahost",
]

# Kuratierte Förderungen (Stand 2025/2026)
_FOERDERUNGEN: list[dict] = [
    {
        "name": "EAG Investitionszuschuss PV",
        "beschreibung": "Bis zu 285 €/kWp für Photovoltaik-Anlagen bis 1000 kWp.",
        "betrag_text": "285 €/kWp",
        "bundesland": "",
        "zielgruppe": "Privatpersonen, Unternehmen",
        "url": "https://www.klimafonds.gv.at/",
    },
    {
        "name": "Balkonkraftwerk-Förderung",
        "beschreibung": "420€ Pauschalförderung für steckerfertige PV-Anlagen bis 800W.",
        "betrag_text": "420 €",
        "bundesland": "",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.klimafonds.gv.at/",
    },
    {
        "name": "Sanierungsbonus",
        "beschreibung": "Bis zu 42.000€ für thermische Gebäudesanierung.",
        "betrag_text": "bis 42.000 €",
        "bundesland": "",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.umweltfoerderung.at/",
    },
    {
        "name": "Raus aus Öl und Gas",
        "beschreibung": "Bis zu 7.500€ für den Umstieg von fossiler Heizung auf klimafreundliche Systeme.",
        "betrag_text": "bis 7.500 €",
        "bundesland": "",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.umweltfoerderung.at/",
    },
    {
        "name": "Wien: Photovoltaik-Förderung",
        "beschreibung": "Zusätzlich 250 €/kWp für PV-Anlagen in Wien.",
        "betrag_text": "250 €/kWp",
        "bundesland": "Wien",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.wien.gv.at/",
    },
    {
        "name": "NÖ: Stromspeicher-Förderung",
        "beschreibung": "200 €/kWh für Batteriespeicher in Niederösterreich.",
        "betrag_text": "200 €/kWh",
        "bundesland": "Niederösterreich",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.noe.gv.at/",
    },
    {
        "name": "OÖ: PV & Speicher Förderung",
        "beschreibung": "Bis zu 1.500€ für PV-Anlagen und Speicher in Oberösterreich.",
        "betrag_text": "bis 1.500 €",
        "bundesland": "Oberösterreich",
        "zielgruppe": "Privatpersonen",
        "url": "https://www.land-oberoesterreich.gv.at/",
    },
]

# PLZ → Bundesland Mapping (erste Ziffer)
_PLZ_BUNDESLAND: dict[str, str] = {
    "1": "Wien",
    "2": "Niederösterreich",
    "3": "Niederösterreich",
    "4": "Oberösterreich",
    "5": "Salzburg",
    "6": "Tirol",
    "7": "Burgenland",
    "8": "Steiermark",
    "9": "Kärnten",
}


def monitor_energy_news(
    user_plz: str = "",
    user_interests: list[str] | None = None,
    heating_type: str = "",
) -> EnergyMonitorResult:
    """Energie-Nachrichten, Preiswarnung und Förderungen abrufen.

    Args:
        user_plz: PLZ des Users für regionale Filterung.
        user_interests: User-Interessen (z.B. ["pv", "spot", "bkw"]).
        heating_type: Heizungsart (z.B. "gas", "strom", "fernwärme").

    Returns:
        EnergyMonitorResult mit Nachrichten, Förderungen und ggf. Preiswarnung.
    """
    nachrichten = _fetch_energy_news()
    foerderungen = _filter_foerderungen(user_plz)
    preis_warnung = _check_price_alert()

    return EnergyMonitorResult(
        nachrichten=nachrichten,
        foerderungen=foerderungen,
        preis_warnung=preis_warnung,
    )


def _fetch_energy_news() -> list[EnergyNewsItem]:
    """Energie-relevante Nachrichten aus RSS-Feeds laden."""
    all_items: list[EnergyNewsItem] = []

    for feed in _RSS_FEEDS:
        try:
            items = _parse_rss_feed(feed["url"], feed["name"], feed["kategorie"])
            all_items.extend(items)
        except Exception as exc:
            log.debug("RSS Feed %s fehlgeschlagen: %s", feed["name"], exc)

    # Nach Relevanz filtern
    relevant = [item for item in all_items if _is_energy_relevant(item.titel + " " + item.zusammenfassung)]

    # Nach Datum sortieren (neueste zuerst), maximal 10
    relevant.sort(key=lambda x: x.datum or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return relevant[:10]


def _parse_rss_feed(url: str, source_name: str, kategorie: str) -> list[EnergyNewsItem]:
    """RSS Feed parsen und EnergyNewsItems erstellen."""
    items: list[EnergyNewsItem] = []

    resp = httpx.get(url, timeout=15, follow_redirects=True)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)

    for item in root.iter("item"):
        title = item.findtext("title", "")
        description = item.findtext("description", "")
        link = item.findtext("link", "")
        pub_date_str = item.findtext("pubDate", "")

        datum = None
        if pub_date_str:
            try:
                datum = datetime.strptime(pub_date_str[:25], "%a, %d %b %Y %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                pass

        items.append(EnergyNewsItem(
            titel=title.strip(),
            zusammenfassung=_clean_html(description)[:300],
            quelle=source_name,
            url=link.strip(),
            datum=datum,
            kategorie=kategorie,
        ))

    return items


def _is_energy_relevant(text: str) -> bool:
    """Prüfen ob ein Text energie-relevant ist."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in _ENERGY_KEYWORDS)


def _clean_html(text: str) -> str:
    """Einfache HTML-Tag-Entfernung."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _filter_foerderungen(plz: str) -> list[Foerderung]:
    """Förderungen nach PLZ/Bundesland filtern."""
    bundesland = ""
    if plz:
        bundesland = _PLZ_BUNDESLAND.get(plz[0], "")

    result: list[Foerderung] = []
    for f in _FOERDERUNGEN:
        # Bundesweite Förderungen immer inkludieren
        if not f["bundesland"] or f["bundesland"] == bundesland:
            result.append(Foerderung(
                name=f["name"],
                beschreibung=f["beschreibung"],
                betrag_text=f["betrag_text"],
                bundesland=f.get("bundesland", ""),
                zielgruppe=f.get("zielgruppe", ""),
                url=f.get("url", ""),
            ))

    return result


def _check_price_alert() -> str:
    """Spot-Preis-Warnung prüfen (vereinfacht)."""
    try:
        from gridbert.config import ENTSOE_API_KEY

        if not ENTSOE_API_KEY:
            return ""

        # Simplifiziert — in Zukunft: ENTSO-E day-ahead prices prüfen
        # und mit 30-Tage-Durchschnitt vergleichen
        return ""
    except Exception:
        return ""
