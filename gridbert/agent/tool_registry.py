# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Tool Registry: Registriert Tools mit Claude API-kompatiblen Definitionen."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from gridbert.agent.types import ToolDefinition

log = logging.getLogger(__name__)


class ToolRegistry:
    """Registry für Agent-Tools.

    Mappt Tool-Namen auf Python-Funktionen und generiert
    Claude API tool definitions.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Registriere ein Tool mit Claude API Definition und Handler."""
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
        )
        self._handlers[name] = handler
        log.debug("Tool registriert: %s", name)

    def definitions(self) -> list[dict[str, Any]]:
        """Claude API tool definitions zurückgeben."""
        return [
            {
                "name": defn.name,
                "description": defn.description,
                "input_schema": defn.input_schema,
            }
            for defn in self._definitions.values()
        ]

    def execute(self, name: str, input_data: dict[str, Any]) -> str:
        """Tool ausführen und Ergebnis als String zurückgeben."""
        handler = self._handlers.get(name)
        if handler is None:
            return f"Unbekanntes Tool: {name}"

        log.info("Tool ausführen: %s", name)
        try:
            result = handler(**input_data)
            # Pydantic-Models automatisch serialisieren
            if hasattr(result, "model_dump_json"):
                return result.model_dump_json(indent=2)
            return str(result)
        except Exception as e:
            log.error("Tool %s fehlgeschlagen: %s", name, e)
            return f"Fehler bei {name}: {e}"

    @property
    def tool_names(self) -> list[str]:
        return list(self._definitions.keys())


def build_default_registry() -> ToolRegistry:
    """Erstelle Registry mit allen Gridbert-Tools."""
    registry = ToolRegistry()

    # --- Invoice Parser -------------------------------------------------------
    from gridbert.tools.invoice_parser import parse_invoice

    registry.register(
        name="parse_invoice",
        description=(
            "Analysiere eine Stromrechnung (PDF oder Bild). "
            "Extrahiert Lieferant, Tarif, Energiepreis, Grundgebühr, "
            "Jahresverbrauch, PLZ und Zählpunkt."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Pfad zur hochgeladenen Rechnungsdatei",
                },
            },
            "required": ["file_path"],
        },
        handler=parse_invoice,
    )

    # --- Smart Meter (Multi-Provider) -----------------------------------------
    from gridbert.tools.smartmeter_providers import fetch_smart_meter_multi, get_available_providers

    registry.register(
        name="fetch_smart_meter_data",
        description=(
            "Hole Smart-Meter-Verbrauchsdaten vom Netzbetreiber des Users. "
            "Unterstützt mehrere österreichische Netzbetreiber. "
            "Aktuell implementiert: Wiener Netze. "
            "Gibt 15-Minuten-Messwerte, hochgerechneten Jahresverbrauch "
            "und Grundlast zurück."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "provider_id": {
                    "type": "string",
                    "description": (
                        "ID des Netzbetreibers: wiener_netze, netz_noe, netz_ooe, "
                        "salzburg_netz, tinetz, energienetze_stmk, kaernten_netz"
                    ),
                    "default": "wiener_netze",
                },
                "email": {
                    "type": "string",
                    "description": "Login E-Mail für das Smart Meter Portal",
                },
                "password": {
                    "type": "string",
                    "description": "Passwort für das Smart Meter Portal",
                },
                "zaehlpunkt": {
                    "type": "string",
                    "description": "Zählpunktnummer (optional, wird automatisch ermittelt)",
                    "default": "",
                },
            },
            "required": ["email", "password"],
        },
        handler=lambda provider_id="wiener_netze", email="", password="", zaehlpunkt="": (
            fetch_smart_meter_multi(
                provider_id=provider_id,
                credentials={"email": email, "password": password},
                zaehlpunkt=zaehlpunkt,
            )
        ),
    )

    registry.register(
        name="list_smart_meter_providers",
        description=(
            "Liste alle verfügbaren Smart Meter Netzbetreiber auf. "
            "Zeigt welche Provider implementiert sind und welche geplant."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=lambda: get_available_providers(),
    )

    # --- Tariff Compare -------------------------------------------------------
    from gridbert.tools.tariff_compare import compare_tariffs

    registry.register(
        name="compare_tariffs",
        description=(
            "Vergleiche Stromtarife über den E-Control Tarifkalkulator. "
            "Findet günstigere Alternativen zum aktuellen Tarif."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "plz": {"type": "string", "description": "Postleitzahl"},
                "jahresverbrauch_kwh": {"type": "number", "description": "Jahresverbrauch in kWh"},
                "aktueller_lieferant": {"type": "string", "description": "Name des aktuellen Lieferanten"},
                "aktueller_energiepreis": {"type": "number", "description": "Aktueller Energiepreis in ct/kWh brutto"},
                "aktuelle_grundgebuehr": {"type": "number", "description": "Aktuelle Grundgebühr in €/Monat brutto"},
            },
            "required": ["plz", "jahresverbrauch_kwh", "aktueller_lieferant", "aktueller_energiepreis", "aktuelle_grundgebuehr"],
        },
        handler=compare_tariffs,
    )

    # --- BEG Advisor ----------------------------------------------------------
    from gridbert.tools.beg_advisor import compare_beg_options

    registry.register(
        name="compare_beg_options",
        description=(
            "Vergleiche Bürgerenergiegemeinschaften (BEG). "
            "Berechnet Ersparnis und Amortisation für bekannte BEG-Anbieter."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "jahresverbrauch_kwh": {"type": "number", "description": "Jahresverbrauch in kWh"},
                "aktueller_energiepreis_ct_kwh": {"type": "number", "description": "Aktueller Energiepreis in ct/kWh brutto"},
            },
            "required": ["jahresverbrauch_kwh", "aktueller_energiepreis_ct_kwh"],
        },
        handler=compare_beg_options,
    )

    # --- Report Generation ----------------------------------------------------
    from gridbert.models import SavingsReport
    from gridbert.report import generate_report

    def _generate_report_tool(
        invoice_json: str,
        tariff_comparison_json: str = "",
        beg_comparison_json: str = "",
        smart_meter_json: str = "",
    ) -> str:
        """Wrapper: Baut SavingsReport aus JSON-Strings und generiert Markdown."""
        import json

        from gridbert.models import BEGComparison, Invoice, SmartMeterData, TariffComparison

        data: dict = {"invoice": Invoice(**json.loads(invoice_json))}
        if tariff_comparison_json:
            data["tariff_comparison"] = TariffComparison(**json.loads(tariff_comparison_json))
        if beg_comparison_json:
            data["beg_comparison"] = BEGComparison(**json.loads(beg_comparison_json))
        if smart_meter_json:
            data["smart_meter"] = SmartMeterData(**json.loads(smart_meter_json))

        report = SavingsReport(**data)
        return generate_report(report)

    registry.register(
        name="generate_savings_report",
        description=(
            "Erstelle einen Einsparungs-Report als Markdown. "
            "Benötigt mindestens die Rechnungsdaten (invoice_json)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "invoice_json": {"type": "string", "description": "Invoice als JSON-String"},
                "tariff_comparison_json": {"type": "string", "description": "TariffComparison als JSON-String (optional)"},
                "beg_comparison_json": {"type": "string", "description": "BEGComparison als JSON-String (optional)"},
                "smart_meter_json": {"type": "string", "description": "SmartMeterData als JSON-String (optional)"},
            },
            "required": ["invoice_json"],
        },
        handler=_generate_report_tool,
    )

    # --- Load Profile Analysis ------------------------------------------------
    from gridbert.tools.load_profile import analyze_load_profile

    registry.register(
        name="analyze_load_profile",
        description=(
            "Analysiere ein Lastprofil (15-Minuten-Verbrauchsdaten). "
            "Berechnet Grundlast, Spitzenlast, Volllaststunden, erkennt Anomalien, "
            "schätzt Einsparpotenziale und erstellt Visualisierungen (Heatmap, "
            "Jahresdauerlinie, Monatsverbrauch)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "consumption_data": {
                    "type": "array",
                    "description": "15-Minuten-Verbrauchsdaten als Liste von {timestamp, kwh}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "kwh": {"type": "number"},
                        },
                    },
                },
                "price_per_kwh": {
                    "type": "number",
                    "description": "Strompreis in EUR/kWh brutto (default: 0.20)",
                    "default": 0.20,
                },
            },
            "required": ["consumption_data"],
        },
        handler=analyze_load_profile,
    )

    # --- Spot Tariff Analysis -------------------------------------------------
    from gridbert.tools.spot_analysis import analyze_spot_tariff

    registry.register(
        name="analyze_spot_tariff",
        description=(
            "Analysiere ob ein Spot-Tarif günstiger wäre. Berechnet "
            "volumengewichteten Durchschnittspreis, Profilkostenfaktor und "
            "vergleicht mit Fix-Tarif. Benötigt Lastprofil-Daten."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "consumption_data": {
                    "type": "array",
                    "description": "15-Minuten-Verbrauchsdaten als Liste von {timestamp, kwh}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "kwh": {"type": "number"},
                        },
                    },
                },
                "fix_preis_ct": {
                    "type": "number",
                    "description": "Aktueller Fix-Preis in ct/kWh brutto (default: 20)",
                    "default": 20.0,
                },
            },
            "required": ["consumption_data"],
        },
        handler=analyze_spot_tariff,
    )

    # --- Battery Simulator ----------------------------------------------------
    from gridbert.tools.battery_sim import simulate_battery

    registry.register(
        name="simulate_battery",
        description=(
            "Simuliere verschiedene Batteriespeicher-Szenarien (2, 5, 10, 15 kWh). "
            "Berechnet Ersparnis und Amortisation. Benötigt Lastprofil-Daten."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "consumption_data": {
                    "type": "array",
                    "description": "15-Minuten-Verbrauchsdaten als Liste von {timestamp, kwh}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "kwh": {"type": "number"},
                        },
                    },
                },
                "tarif_preis_ct": {
                    "type": "number",
                    "description": "Aktueller Strompreis in ct/kWh brutto (default: 20)",
                    "default": 20.0,
                },
            },
            "required": ["consumption_data"],
        },
        handler=simulate_battery,
    )

    # --- PV / Balkonkraftwerk Simulator ---------------------------------------
    from gridbert.tools.pv_sim import simulate_pv

    registry.register(
        name="simulate_pv",
        description=(
            "Simuliere eine PV-Anlage oder Balkonkraftwerk. Nutzt die PVGIS API "
            "für Ertragsschätzung. Berechnet Eigenverbrauch, Ersparnis, Förderung "
            "und Amortisation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "plz": {"type": "string", "description": "Postleitzahl"},
                "anlage_kwp": {
                    "type": "number",
                    "description": "Anlagengröße in kWp (0.8 für BKW, 3-15 für Dach)",
                    "default": 0.8,
                },
                "ausrichtung": {
                    "type": "string",
                    "description": "Ausrichtung: Süd, Südost, Südwest, Ost, West",
                    "default": "Süd",
                },
                "neigung": {
                    "type": "integer",
                    "description": "Neigungswinkel in Grad (default: 35)",
                    "default": 35,
                },
                "jahresverbrauch_kwh": {
                    "type": "number",
                    "description": "Jährlicher Stromverbrauch in kWh",
                    "default": 3200.0,
                },
                "strompreis_ct": {
                    "type": "number",
                    "description": "Aktueller Strompreis in ct/kWh brutto",
                    "default": 20.0,
                },
            },
            "required": ["plz"],
        },
        handler=simulate_pv,
    )

    # --- Gas Tariff Comparison ------------------------------------------------
    from gridbert.tools.gas_compare import compare_gas_tariffs

    registry.register(
        name="compare_gas_tariffs",
        description=(
            "Vergleiche Gas-Tarife über den E-Control Tarifkalkulator. "
            "Funktioniert analog zum Strom-Tarifvergleich."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "plz": {"type": "string", "description": "Postleitzahl"},
                "jahresverbrauch_kwh": {
                    "type": "number",
                    "description": "Jährlicher Gasverbrauch in kWh (default: 15000)",
                    "default": 15000.0,
                },
            },
            "required": ["plz"],
        },
        handler=compare_gas_tariffs,
    )

    # --- Energy News & Impact Monitor -----------------------------------------
    from gridbert.tools.energy_monitor import monitor_energy_news

    registry.register(
        name="monitor_energy_news",
        description=(
            "Prüfe aktuelle Energie-Nachrichten, Marktentwicklungen und "
            "verfügbare Förderungen. Gibt geopolitische Events, Preisalarme "
            "und personalisierte Förder-Empfehlungen zurück."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "user_plz": {
                    "type": "string",
                    "description": "PLZ des Users für regionale Förderfilterung",
                    "default": "",
                },
                "user_interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "User-Interessen (z.B. pv, spot, bkw, batterie)",
                    "default": [],
                },
                "heating_type": {
                    "type": "string",
                    "description": "Heizungsart (gas, strom, fernwärme, öl)",
                    "default": "",
                },
            },
        },
        handler=monitor_energy_news,
    )

    return registry
