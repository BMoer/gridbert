# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Wiener Netze Smart Meter Provider — Wrapper um bestehenden SmartMeterClient."""

from __future__ import annotations

from gridbert.models import SmartMeterData
from gridbert.tools.smartmeter import SmartMeterClient


class WienerNetzeProvider:
    """Smart Meter Provider für Wiener Netze (PKCE OAuth via log.wien)."""

    @property
    def name(self) -> str:
        return "Wiener Netze"

    @property
    def supported_regions(self) -> list[str]:
        return ["1"]  # Wien = PLZ 1xxx

    def fetch_data(
        self, credentials: dict[str, str], zaehlpunkt: str = ""
    ) -> SmartMeterData:
        """Verbrauchsdaten über die Wiener Netze API holen."""
        email = credentials.get("email", "")
        password = credentials.get("password", "")

        if not email or not password:
            raise ValueError("Wiener Netze benötigt 'email' und 'password' in credentials.")

        client = SmartMeterClient(email, password)
        try:
            zp_list = client.get_zaehlpunkte()
            if not zp_list:
                raise RuntimeError("Keine Zählpunkte gefunden — ist ein Smart Meter aktiv?")

            target = None
            if zaehlpunkt:
                target = next((z for z in zp_list if z["zaehlpunkt"] == zaehlpunkt), None)
            if not target:
                target = zp_list[0]

            return client.get_verbrauch(
                customer_id=target["geschaeftspartner"],
                zaehlpunkt=target["zaehlpunkt"],
            )
        finally:
            client.close()
