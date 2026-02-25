# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Wiener Netze Smart Meter Daten via API (PKCE Auth über log.wien)."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx

from gridbert.models import ConsumptionReading, SmartMeterData

log = logging.getLogger(__name__)

# --- Endpoints (Stand Februar 2026, via DarwinsBuddy/WienerNetzeSmartmeter) ---
_AUTH_BASE = "https://log.wien/auth/realms/logwien/protocol/openid-connect/"
_API_URL = "https://api.wstw.at/gateway/WN_SMART_METER_PORTAL_API_B2C/1.0"
_API_URL_ALT = "https://service.wienernetze.at/sm/api/"
_API_CONFIG_URL = "https://smartmeter-web.wienernetze.at/assets/app-config.json"
_REDIRECT_URI = "https://smartmeter-web.wienernetze.at/"
_CLIENT_ID = "wn-smartmeter"


def _generate_pkce() -> tuple[str, str]:
    """PKCE code_verifier + code_challenge (S256) generieren."""
    verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    challenge = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")
    return verifier, challenge_b64


class SmartMeterClient:
    """Client für die Wiener Netze Smart Meter API (log.wien PKCE)."""

    def __init__(self, email: str, password: str) -> None:
        self._email = email
        self._password = password
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            follow_redirects=False,  # Wir brauchen die Location-Header
        )
        self._access_token: str | None = None
        self._api_key: str | None = None

    def _authenticate(self) -> None:
        """PKCE OAuth2 Login über log.wien."""
        log.info("Authentifiziere bei Wiener Netze (log.wien)...")

        code_verifier, code_challenge = _generate_pkce()

        # Step 1: Login-Seite laden (mit PKCE Challenge)
        login_params = {
            "client_id": _CLIENT_ID,
            "redirect_uri": _REDIRECT_URI,
            "response_mode": "fragment",
            "response_type": "code",
            "scope": "openid",
            "nonce": "",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        login_url = _AUTH_BASE + "auth?" + urlencode(login_params)

        resp = self._http.get(login_url, follow_redirects=True)
        resp.raise_for_status()

        # Action-URL aus dem Login-Formular extrahieren
        action_match = re.search(r'action="([^"]+)"', resp.text)
        if not action_match:
            raise RuntimeError(
                "Login-Seite hat kein action-Attribut — HTML-Struktur hat sich geändert?"
            )
        action_url = action_match.group(1).replace("&amp;", "&")

        # Step 2a: Username absenden (log.wien hat Zwei-Schritt-Login)
        resp2 = self._http.post(
            action_url,
            data={"username": self._email, "login": " "},
            follow_redirects=False,
        )

        # Zweites Formular extrahieren (Passwort-Seite)
        if resp2.status_code == 200:
            # Direkt die Passwort-Seite bekommen
            action_match2 = re.search(r'action="([^"]+)"', resp2.text)
            if action_match2:
                action_url2 = action_match2.group(1).replace("&amp;", "&")
            else:
                action_url2 = action_url
        elif resp2.is_redirect:
            action_url2 = str(resp2.headers.get("Location", action_url))
        else:
            action_url2 = action_url

        # Step 2b: Passwort absenden
        resp3 = self._http.post(
            action_url2,
            data={"username": self._email, "password": self._password},
            follow_redirects=False,
        )

        # Step 3: Authorization Code aus Redirect-Location extrahieren
        if "Location" not in resp3.headers:
            raise RuntimeError(
                "Login fehlgeschlagen — falsche Credentials oder 2FA aktiv?"
            )
        location = resp3.headers["Location"]

        # Code ist im URL-Fragment: ...#code=XXXXX&...
        parsed = urlparse(location)
        fragment_parts = dict(
            part.split("=", 1) for part in parsed.fragment.split("&") if "=" in part
        )
        code = fragment_parts.get("code")
        if not code:
            raise RuntimeError(
                f"Kein 'code' in Redirect-Fragment — Login fehlgeschlagen? Location: {location[:200]}"
            )

        # Step 4: Code + Verifier gegen Token tauschen
        token_resp = self._http.post(
            _AUTH_BASE + "token",
            data={
                "grant_type": "authorization_code",
                "client_id": _CLIENT_ID,
                "redirect_uri": _REDIRECT_URI,
                "code": code,
                "code_verifier": code_verifier,
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()
        self._access_token = tokens["access_token"]
        log.info("Authentifizierung erfolgreich (Token gültig %ds)", tokens.get("expires_in", 0))

        # Step 5: API Gateway Key aus App-Config holen
        config_resp = self._http.get(
            _API_CONFIG_URL,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        config_resp.raise_for_status()
        config = config_resp.json()
        self._api_key = config.get("b2cApiKey", "")
        if not self._api_key:
            log.warning("Kein b2cApiKey in App-Config — API-Calls könnten fehlschlagen")

    def _api_get(self, path: str, params: dict | None = None, base_url: str | None = None) -> dict:
        """Authentifizierter API-Call."""
        if not self._access_token:
            self._authenticate()

        url = (base_url or _API_URL).rstrip("/") + "/" + path.lstrip("/")
        headers: dict[str, str] = {"Authorization": f"Bearer {self._access_token}"}
        if self._api_key:
            headers["X-Gateway-APIKey"] = self._api_key

        response = self._http.get(url, params=params, headers=headers, follow_redirects=True)
        response.raise_for_status()
        return response.json()

    def get_zaehlpunkte(self) -> list[dict]:
        """Alle Zählpunkte des Benutzers mit Geschäftspartner-IDs."""
        data = self._api_get("zaehlpunkte")
        # API gibt Liste von Verträgen zurück:
        # [{"geschaeftspartner": "...", "zaehlpunkte": [{"zaehlpunktnummer": "AT00..."}]}]
        results = []
        if isinstance(data, list):
            for contract in data:
                gp = contract.get("geschaeftspartner", "")
                for zp in contract.get("zaehlpunkte", []):
                    zpnr = zp.get("zaehlpunktnummer", "")
                    if zpnr:
                        results.append({"zaehlpunkt": zpnr, "geschaeftspartner": gp})
        return results

    def get_verbrauch(
        self,
        customer_id: str,
        zaehlpunkt: str,
        von: datetime | None = None,
        bis: datetime | None = None,
    ) -> SmartMeterData:
        """15-Minuten-Verbrauchsdaten über den Legacy-Endpoint holen.

        Nutzt ``bewegungsdaten`` auf service.wienernetze.at (funktioniert,
        während der neue B2C ``messdaten`` Endpoint 404 gibt).
        """
        if bis is None:
            bis = datetime.now(tz=timezone.utc)
        if von is None:
            von = bis - timedelta(days=90)

        params = {
            "geschaeftspartner": customer_id,
            "zaehlpunktnummer": zaehlpunkt,
            "rolle": "V002",  # Viertelstunden-Verbrauch
            "zeitpunktVon": von.strftime("%Y-%m-%dT00:00:00.000Z"),
            "zeitpunktBis": bis.strftime("%Y-%m-%dT23:59:59.999Z"),
            "aggregat": "NONE",
        }

        log.info("Hole Verbrauchsdaten für %s (%s bis %s)", zaehlpunkt, von.date(), bis.date())
        data = self._api_get(
            "user/messwerte/bewegungsdaten",
            params=params,
            base_url=_API_URL_ALT,
        )

        readings: list[ConsumptionReading] = []

        # Antwort-Format: {"descriptor": {...}, "values": [{"wert": 0.013, "zeitpunktVon": "...", ...}]}
        values = []
        if isinstance(data, dict):
            values = data.get("values", [])
        elif isinstance(data, list):
            # Fallback: alte Liste-von-Tagen Struktur
            for entry in data:
                values.extend(entry.get("values", entry.get("wpiList", [])))

        for val in values:
            ts = val.get("zeitpunktVon")
            wert = val.get("wert")
            if ts and wert is not None:
                try:
                    readings.append(ConsumptionReading(
                        timestamp=datetime.fromisoformat(ts.replace("Z", "+00:00")),
                        kwh=float(wert),
                    ))
                except (ValueError, TypeError):
                    continue

        log.info("Erhalten: %d Messwerte (15-min Intervalle)", len(readings))
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
        # Zählpunkte holen
        zp_list = client.get_zaehlpunkte()
        if not zp_list:
            raise RuntimeError("Keine Zählpunkte gefunden — ist ein Smart Meter aktiv?")

        log.info("Gefundene Zählpunkte: %s", [z["zaehlpunkt"] for z in zp_list])

        # Gewünschten oder ersten Zählpunkt verwenden
        target = None
        if zaehlpunkt:
            target = next((z for z in zp_list if z["zaehlpunkt"] == zaehlpunkt), None)
        if not target:
            target = zp_list[0]
            log.info("Verwende Zählpunkt: %s (Geschäftspartner: %s)",
                     target["zaehlpunkt"], target["geschaeftspartner"])

        return client.get_verbrauch(
            customer_id=target["geschaeftspartner"],
            zaehlpunkt=target["zaehlpunkt"],
        )
    finally:
        client.close()
