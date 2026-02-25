# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Wiener Netze Smart Meter Daten via API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from gridbert.models import ConsumptionReading, SmartMeterData

log = logging.getLogger(__name__)

# Wiener Netze API Endpunkte (basierend auf vienna-smartmeter Reverse-Engineering)
_BASE_URL = "https://service.wienernetze.at"
_AUTH_URL = "https://log.wienernetze.at/auth/realms/wn/protocol/openid-connect/token"
_API_BASE = f"{_BASE_URL}/sm/api"
_CLIENT_ID = "wn-smartmeter"

# Keycloak Auth
_REDIRECT_URI = f"{_BASE_URL}/sm/app/"


class SmartMeterClient:
    """Client für die Wiener Netze Smart Meter API."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._http = httpx.Client(timeout=30, follow_redirects=True)
        self._access_token: str | None = None

    def _authenticate(self) -> None:
        """Keycloak Resource Owner Password Grant."""
        log.info("Authentifiziere bei Wiener Netze...")

        # Step 1: Login-Seite holen um Session-Cookies zu bekommen
        login_page = self._http.get(
            f"https://log.wienernetze.at/auth/realms/wn/protocol/openid-connect/auth",
            params={
                "client_id": _CLIENT_ID,
                "redirect_uri": _REDIRECT_URI,
                "response_mode": "fragment",
                "response_type": "code",
                "scope": "openid",
            },
        )

        # Step 2: Login-Form absenden (Action-URL aus der Seite extrahieren)
        import re

        action_match = re.search(r'action="([^"]+)"', login_page.text)
        if not action_match:
            raise RuntimeError("Login-Seite hat kein action-Attribut — API hat sich geändert?")

        action_url = action_match.group(1).replace("&amp;", "&")

        login_response = self._http.post(
            action_url,
            data={"username": self._email, "password": self._password},
        )

        # Step 3: Authorization Code aus Redirect extrahieren
        if "code=" not in str(login_response.url):
            raise RuntimeError(
                "Login fehlgeschlagen — falsche Credentials oder API-Änderung"
            )

        code = str(login_response.url).split("code=")[1].split("&")[0]

        # Step 4: Code gegen Token tauschen
        token_response = self._http.post(
            _AUTH_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": _CLIENT_ID,
                "code": code,
                "redirect_uri": _REDIRECT_URI,
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        self._access_token = token_data["access_token"]
        log.info("Authentifizierung erfolgreich")

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        if not self._access_token:
            self._authenticate()

        response = self._http.get(
            f"{_API_BASE}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        return response.json()

    def get_zaehlpunkte(self) -> list[str]:
        """Alle Zählpunkte des Benutzers abrufen."""
        data = self._api_get("/user/messwerte/zaehlpunkte")
        # API gibt Liste von Objekten mit "zaehlpunktnummer" zurück
        if isinstance(data, list):
            return [z.get("zaehlpunktnummer", "") for z in data if z.get("zaehlpunktnummer")]
        return []

    def get_verbrauch(
        self,
        zaehlpunkt: str,
        von: datetime | None = None,
        bis: datetime | None = None,
    ) -> SmartMeterData:
        """15-Minuten-Verbrauchsdaten für einen Zeitraum holen."""
        if bis is None:
            bis = datetime.now(tz=timezone.utc)
        if von is None:
            von = bis - timedelta(days=90)  # 3 Monate

        params = {
            "zaehlpunktnummer": zaehlpunkt,
            "rolle": "V002",
            "zeitpunktVon": von.strftime("%Y-%m-%dT00:00:00.000Z"),
            "zeitpunktBis": bis.strftime("%Y-%m-%dT23:59:59.999Z"),
            "aggregat": "NONE",
        }

        log.info("Hole Verbrauchsdaten für %s (%s bis %s)", zaehlpunkt, von.date(), bis.date())
        data = self._api_get("/user/messwerte/bewegungsdaten", params)

        readings: list[ConsumptionReading] = []
        # API-Antwort: Liste von Tageswerten mit "wpiList" (15-min-Werte)
        if isinstance(data, list):
            for day_entry in data:
                for reading in day_entry.get("wpiList", []):
                    ts = reading.get("zeitpunktVon")
                    val = reading.get("wert")
                    if ts and val is not None:
                        readings.append(
                            ConsumptionReading(
                                timestamp=datetime.fromisoformat(ts),
                                kwh=float(val),
                            )
                        )

        return SmartMeterData(
            zaehlpunkt=zaehlpunkt,
            readings=readings,
            zeitraum_von=von,
            zeitraum_bis=bis,
        )

    def close(self) -> None:
        self._http.close()


def fetch_smart_meter_data(email: str, password: str, zaehlpunkt: str = "") -> SmartMeterData:
    """Convenience-Funktion: Login + Daten holen."""
    client = SmartMeterClient(email, password)
    try:
        if not zaehlpunkt:
            zaehlpunkte = client.get_zaehlpunkte()
            if not zaehlpunkte:
                raise RuntimeError("Keine Zählpunkte gefunden — ist ein Smart Meter aktiv?")
            zaehlpunkt = zaehlpunkte[0]
            log.info("Verwende Zählpunkt: %s", zaehlpunkt)

        return client.get_verbrauch(zaehlpunkt)
    finally:
        client.close()
