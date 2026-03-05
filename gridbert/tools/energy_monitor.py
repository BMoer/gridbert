# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Energy News & Impact Monitor — Nachrichten, Preise, Förderungen.

Three pillars:
1. Geopolitics & Markets — RSS feeds + Claude summarization
2. Spot & Wholesale Prices — ENTSO-E price alerts
3. Förderungen & Subsidies — Curated JSON catalog filtered by user profile
"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

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

# Förderungskatalog-Pfad
_FOERDERUNGEN_PATH = Path(__file__).parent.parent / "data" / "foerderungen.json"

# Warnung wenn Katalog älter als 60 Tage
_KATALOG_MAX_AGE_DAYS = 60


def load_foerderungen_catalog() -> tuple[list[dict], str]:
    """Lade Förderungskatalog aus JSON-Datei.

    Returns:
        Tuple von (Liste der Förderungen, Stand-Datum des Katalogs).
    """
    try:
        raw = _FOERDERUNGEN_PATH.read_text(encoding="utf-8")
        catalog = json.loads(raw)
        stand = catalog.get("_meta", {}).get("stand", "unbekannt")
        return catalog.get("foerderungen", []), stand
    except Exception as exc:
        log.error("Förderungskatalog konnte nicht geladen werden: %s", exc)
        return [], "unbekannt"


def _check_catalog_freshness(stand: str) -> str:
    """Prüfe ob der Katalog aktuell ist. Gibt Warntext zurück wenn veraltet."""
    if not stand or stand == "unbekannt":
        return "Förderungskatalog: Stand unbekannt — Angaben bitte selbst verifizieren."

    try:
        stand_date = date.fromisoformat(stand)
        age_days = (date.today() - stand_date).days
        if age_days > _KATALOG_MAX_AGE_DAYS:
            return (
                f"Förderungskatalog ist {age_days} Tage alt (Stand: {stand}). "
                "Angaben könnten veraltet sein — bitte offizielle Quellen prüfen."
            )
    except ValueError:
        return "Förderungskatalog: Stand-Datum ungültig."

    return ""


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
    foerderungen_raw, katalog_stand = load_foerderungen_catalog()
    foerderungen = _filter_foerderungen(foerderungen_raw, user_plz, user_interests)
    preis_warnung = _check_price_alert()

    freshness_warning = _check_catalog_freshness(katalog_stand)
    zusammenfassung = freshness_warning

    return EnergyMonitorResult(
        nachrichten=nachrichten,
        foerderungen=foerderungen,
        preis_warnung=preis_warnung,
        zusammenfassung=zusammenfassung,
        katalog_stand=katalog_stand,
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


def _filter_foerderungen(
    catalog: list[dict],
    plz: str,
    user_interests: list[str] | None = None,
) -> list[Foerderung]:
    """Förderungen nach PLZ/Bundesland und Status filtern.

    Only returns active Förderungen matching the user's region.
    Expired ones are excluded unless they were recently active (for reference).
    """
    bundesland = ""
    if plz:
        bundesland = _PLZ_BUNDESLAND.get(plz[0], "")

    today_str = date.today().isoformat()
    result: list[Foerderung] = []

    for f in catalog:
        # Skip expired Förderungen
        if f.get("status") == "ausgelaufen":
            continue

        # Regional filter: include nationwide + matching Bundesland
        f_bl = f.get("bundesland", "")
        if f_bl and f_bl != bundesland:
            continue

        # Check validity dates if present
        gueltig_bis = f.get("gueltig_bis", "")
        if gueltig_bis and gueltig_bis < today_str:
            continue

        result.append(Foerderung(
            name=f["name"],
            beschreibung=f.get("beschreibung", ""),
            betrag_eur=f.get("betrag_eur", 0.0),
            betrag_text=f.get("betrag_text", ""),
            bundesland=f_bl,
            zielgruppe=f.get("zielgruppe", ""),
            kategorie=f.get("kategorie", ""),
            url=f.get("url", ""),
            quelle=f.get("quelle", ""),
            status=f.get("status", "aktiv"),
            gueltig_ab=f.get("gueltig_ab", ""),
            gueltig_bis=gueltig_bis,
            stand=f.get("stand", ""),
            voraussetzungen=f.get("voraussetzungen", ""),
            hinweis=f.get("hinweis", ""),
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
