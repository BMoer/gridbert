# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Netz Niederösterreich Smart Meter Provider — Platzhalter.

TODO: Implementierung basierend auf dem Netz NÖ Smart Meter Portal.
Portal-URL: https://smartmeter.netz-noe.at/
Auth: Vermutlich OAuth2 oder Standard Login.
"""

from __future__ import annotations

from gridbert.models import SmartMeterData


class NetzNOEProvider:
    """Smart Meter Provider für Netz Niederösterreich (noch nicht implementiert)."""

    @property
    def name(self) -> str:
        return "Netz Niederösterreich"

    @property
    def supported_regions(self) -> list[str]:
        return ["2", "3"]  # NÖ = PLZ 2xxx, 3xxx

    def fetch_data(
        self, credentials: dict[str, str], zaehlpunkt: str = ""
    ) -> SmartMeterData:
        raise NotImplementedError(
            "Netz NÖ Smart Meter Anbindung ist noch in Entwicklung. "
            "Bitte lade deine Daten als CSV vom Smart Meter Portal herunter: "
            "https://smartmeter.netz-noe.at/"
        )
