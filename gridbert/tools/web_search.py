# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Web-Suche — DuckDuckGo für Produkt- und Informationsrecherche."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5, region: str = "at-de") -> str:
    """Websuche via DuckDuckGo.

    Args:
        query: Suchbegriff.
        max_results: Maximale Anzahl Ergebnisse (1-10).
        region: Region (at-de für Österreich/Deutsch).

    Returns:
        Formatierte Suchergebnisse als Text.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "Fehler: duckduckgo-search nicht installiert. pip install duckduckgo-search"

    max_results = min(max(1, max_results), 10)

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, max_results=max_results))

        if not results:
            return f"Keine Ergebnisse für '{query}' gefunden."

        lines: list[str] = [f"Suchergebnisse für: {query}\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            href = r.get("href", "")
            body = r.get("body", "")
            lines.append(f"{i}. **{title}**")
            lines.append(f"   {href}")
            if body:
                lines.append(f"   {body}")
            lines.append("")

        return "\n".join(lines)

    except Exception as exc:
        log.error("Web-Suche fehlgeschlagen: %s", exc)
        return f"Fehler bei der Web-Suche: {exc}"
