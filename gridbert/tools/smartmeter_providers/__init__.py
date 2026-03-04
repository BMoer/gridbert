# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Multi-Provider Smart Meter Abstraction.

Each provider implements the SmartMeterProvider protocol.
The agent asks the user which provider they have and uses the right one.
"""

from __future__ import annotations

from typing import Protocol

from gridbert.models import SmartMeterData


class SmartMeterProvider(Protocol):
    """Protocol für Smart Meter Datenquellen."""

    @property
    def name(self) -> str:
        """Anzeigename des Netzbetreibers."""
        ...

    @property
    def supported_regions(self) -> list[str]:
        """Unterstützte PLZ-Bereiche (erste Ziffer)."""
        ...

    def fetch_data(self, credentials: dict[str, str], zaehlpunkt: str = "") -> SmartMeterData:
        """Verbrauchsdaten holen.

        Args:
            credentials: Provider-spezifische Credentials (email, password, etc.)
            zaehlpunkt: Optionale Zählpunktnummer.

        Returns:
            SmartMeterData mit 15-min Readings.
        """
        ...


def get_available_providers() -> list[dict[str, str]]:
    """Alle verfügbaren Provider mit Name und Region."""
    return [
        {
            "id": "wiener_netze",
            "name": "Wiener Netze",
            "regionen": "Wien (PLZ 1xxx)",
            "auth": "E-Mail + Passwort (log.wien)",
        },
        {
            "id": "netz_noe",
            "name": "Netz Niederösterreich",
            "regionen": "Niederösterreich (PLZ 2xxx, 3xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
        {
            "id": "netz_ooe",
            "name": "Netz Oberösterreich",
            "regionen": "Oberösterreich (PLZ 4xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
        {
            "id": "salzburg_netz",
            "name": "Salzburg Netz",
            "regionen": "Salzburg (PLZ 5xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
        {
            "id": "tinetz",
            "name": "TINETZ (Tiroler Netze)",
            "regionen": "Tirol (PLZ 6xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
        {
            "id": "energienetze_stmk",
            "name": "Energienetze Steiermark",
            "regionen": "Steiermark (PLZ 8xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
        {
            "id": "kaernten_netz",
            "name": "Kärnten Netz",
            "regionen": "Kärnten (PLZ 9xxx)",
            "auth": "E-Mail + Passwort",
            "status": "geplant",
        },
    ]


def get_provider(provider_id: str) -> SmartMeterProvider | None:
    """Provider-Instanz anhand ID laden."""
    if provider_id == "wiener_netze":
        from gridbert.tools.smartmeter_providers.wiener_netze import WienerNetzeProvider
        return WienerNetzeProvider()
    # Weitere Provider hier registrieren
    return None


def fetch_smart_meter_multi(
    provider_id: str,
    credentials: dict[str, str],
    zaehlpunkt: str = "",
) -> SmartMeterData:
    """Multi-Provider Smart Meter Daten abrufen.

    Args:
        provider_id: ID des Netzbetreibers (z.B. "wiener_netze").
        credentials: Provider-spezifische Credentials.
        zaehlpunkt: Optionale Zählpunktnummer.

    Returns:
        SmartMeterData.

    Raises:
        ValueError: Wenn Provider nicht gefunden oder nicht implementiert.
    """
    provider = get_provider(provider_id)
    if provider is None:
        available = get_available_providers()
        implemented = [p["id"] for p in available if p.get("status") != "geplant"]
        raise ValueError(
            f"Provider '{provider_id}' nicht gefunden oder noch nicht implementiert. "
            f"Verfügbar: {implemented}"
        )
    return provider.fetch_data(credentials, zaehlpunkt)
