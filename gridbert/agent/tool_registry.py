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


def build_default_registry(
    user_id: int | None = None,
    db_conn: Any | None = None,
    llm_provider: Any | None = None,
) -> ToolRegistry:
    """Erstelle Registry mit allen Gridbert-Tools.

    Args:
        user_id: Aktueller User (für Memory-Tool).
        db_conn: SQLAlchemy Connection (für Memory-Tool).
        llm_provider: LLMProvider instance for tools that need LLM access.
    """
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
        handler=lambda file_path: parse_invoice(file_path, llm_provider=llm_provider),
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
    from gridbert.storage.repositories.file_repo import read_file_content as _read_file_content

    # Shared state: last analysis visualizations (auto-injected into widgets)
    _last_analysis_visuals: dict[str, str] = {}

    def _analyze_load_profile_handler(
        file_id: int = 0,
        csv_text: str = "",
        consumption_data: list[dict] | None = None,
        price_per_kwh: float = 0.20,
    ):
        """Wrapper that resolves file_id to actual file content before analysis."""
        # file_id takes priority — reads full file from disk (no truncation)
        if file_id and not csv_text:
            result = _read_file_content(db_conn, user_id, file_id)
            if result is not None:
                raw_bytes, file_meta = result
                file_name = file_meta["file_name"]
                media_type = file_meta["media_type"]
                if file_name.endswith((".xlsx", ".xls")) or media_type in (
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ):
                    import pandas as pd
                    df = pd.read_excel(_io.BytesIO(raw_bytes))
                    csv_text = df.to_csv(index=False)
                else:
                    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                        try:
                            csv_text = raw_bytes.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        csv_text = raw_bytes.decode("utf-8", errors="replace")

        analysis_result = analyze_load_profile(
            consumption_data=consumption_data,
            csv_text=csv_text,
            price_per_kwh=price_per_kwh,
        )

        # Store visualizations for auto-injection into consumption_chart widget
        _last_analysis_visuals.clear()
        if isinstance(analysis_result, str):
            # Tool returned JSON string — parse and extract visuals
            try:
                import json
                parsed = json.loads(analysis_result)
                vis = parsed.get("visualisierungen", {})
                if vis:
                    _last_analysis_visuals.update(vis)
            except Exception:
                pass
        elif hasattr(analysis_result, "visualisierungen"):
            _last_analysis_visuals.update(analysis_result.visualisierungen or {})

        return analysis_result

    import io as _io

    registry.register(
        name="analyze_load_profile",
        description=(
            "Analysiere ein Lastprofil (15-Minuten-Verbrauchsdaten) und erstelle "
            "Visualisierungen (Heatmap, Jahresdauerlinie, Monatsverbrauch). "
            "Berechnet Grundlast, Spitzenlast, Volllaststunden, erkennt Anomalien "
            "und schätzt Einsparpotenziale. "
            "BEVORZUGT: Nutze file_id um eine gespeicherte CSV/Excel-Datei direkt zu analysieren. "
            "Die Datei-IDs stehen im System-Prompt unter 'Gespeicherte Dateien'. "
            "Kein Smart-Meter-Zugang nötig wenn der User eine Datei hochgeladen hat!"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "integer",
                    "description": (
                        "ID einer gespeicherten CSV/Excel-Datei (BEVORZUGT). "
                        "Liest die Datei direkt und vollständig — kein Kopieren nötig."
                    ),
                },
                "csv_text": {
                    "type": "string",
                    "description": (
                        "CSV-Text als Fallback falls keine file_id verfügbar. "
                        "Spalten werden automatisch erkannt."
                    ),
                },
                "consumption_data": {
                    "type": "array",
                    "description": (
                        "NUR für bereits strukturierte Daten aus anderen Tools (z.B. Smart Meter)."
                    ),
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
        },
        handler=_analyze_load_profile_handler,
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
            "und Amortisation. WICHTIG: Frag den User IMMER nach Ausrichtung und "
            "Neigung bevor du dieses Tool aufrufst."
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
                    "description": (
                        "Ausrichtung des Balkons/Dachs: Süd, Südost, Südwest, Ost, West. "
                        "MUSS vom User erfragt werden — niemals annehmen!"
                    ),
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
            "required": ["plz", "ausrichtung"],
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

    # --- Web Search ---------------------------------------------------------------
    from gridbert.tools.web_search import web_search

    registry.register(
        name="web_search",
        description=(
            "Suche im Web nach aktuellen Informationen, Produktangeboten, Preisen "
            "oder Nachrichten. Nützlich für Balkonkraftwerk-Preise, Batterie-Angebote, "
            "Förderungsdetails oder aktuelle Marktpreise."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Suchbegriff (z.B. 'Balkonkraftwerk 800W Preis Österreich')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximale Anzahl Ergebnisse (1-10, default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        handler=web_search,
    )

    # --- User Memory & File Access (requires user context) ----------------------
    if user_id is not None and db_conn is not None:
        from gridbert.storage.repositories.memory_repo import upsert_memory

        def _update_memory(fact_key: str, fact_value: str) -> str:
            upsert_memory(db_conn, user_id, fact_key, fact_value, source="agent")
            db_conn.commit()
            return f"Gespeichert: {fact_key} = {fact_value}"

        registry.register(
            name="update_user_memory",
            description=(
                "Merke dir einen wichtigen Fakt über den User. Nutze dies um "
                "Informationen zu speichern die in künftigen Gesprächen nützlich sind "
                "(z.B. Name, PLZ, Verbrauch, Lieferant, Heizungsart, Interessen). "
                "Jeder fact_key ist einzigartig pro User — gleicher Key überschreibt den alten Wert."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "fact_key": {
                        "type": "string",
                        "description": (
                            "Schlüssel des Fakts, z.B. 'Name', 'PLZ', 'Jahresverbrauch_kWh', "
                            "'Lieferant', 'Heizungsart', 'Interesse_PV', 'Interesse_Spot'"
                        ),
                    },
                    "fact_value": {
                        "type": "string",
                        "description": "Wert des Fakts, z.B. 'Benjamin', '1060', '3200'",
                    },
                },
                "required": ["fact_key", "fact_value"],
            },
            handler=_update_memory,
        )

        # --- Get User File --------------------------------------------------------
        from gridbert.storage.repositories.file_repo import read_file_content
        from gridbert.tools.file_utils import decode_tabular_bytes

        def _get_user_file(file_id: int) -> str:
            result = read_file_content(db_conn, user_id, file_id)
            if result is None:
                return "Fehler: Datei nicht gefunden oder kein Zugriff."

            raw_bytes, file_meta = result
            media_type = file_meta["media_type"]
            file_name = file_meta["file_name"]

            # CSV/Excel → decode to text
            if (
                media_type in (
                    "text/csv",
                    "application/vnd.ms-excel",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                or file_name.endswith((".csv", ".xlsx", ".xls"))
            ):
                return decode_tabular_bytes(raw_bytes, media_type, file_name)

            # PDF → extract text via pdfplumber
            if media_type == "application/pdf" or file_name.endswith(".pdf"):
                try:
                    import pdfplumber

                    import io
                    pages_text = []
                    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                pages_text.append(text)
                    return "\n\n".join(pages_text) if pages_text else "[PDF enthält keinen extrahierbaren Text.]"
                except Exception as exc:
                    return f"[FEHLER: PDF konnte nicht gelesen werden: {exc}]"

            # Images → can't return content as text
            if media_type.startswith("image/"):
                return (
                    f"[Datei {file_name} ist ein Bild ({media_type}). "
                    "Bitte den User bitten, das Bild erneut in dieser Konversation hochzuladen, "
                    "damit du es direkt sehen kannst.]"
                )

            return f"[Dateiformat {media_type} wird nicht unterstützt.]"

        # --- Dashboard Widget (live updates) -----------------------------------------
        import json as _json

        from gridbert.storage.schema import dashboard_widgets

        def _add_dashboard_widget(
            widget_type: str,
            config: dict | None = None,
            position: int = 0,
        ) -> str:
            """Insert or update a dashboard widget for this user."""
            cfg = config or {}

            # Auto-inject base64 visualizations for consumption_chart
            # (Claude can't copy huge base64 strings — we inject them server-side)
            if widget_type == "consumption_chart" and _last_analysis_visuals:
                vis_map = {
                    "heatmap": "heatmap_base64",
                    "jahresdauerlinie": "duration_curve_base64",
                    "monatsverbrauch": "monthly_chart_base64",
                }
                for vis_key, cfg_key in vis_map.items():
                    if cfg_key not in cfg and vis_key in _last_analysis_visuals:
                        cfg[cfg_key] = _last_analysis_visuals[vis_key]
            # Check if widget of same type already exists → update
            existing = db_conn.execute(
                dashboard_widgets.select().where(
                    dashboard_widgets.c.user_id == user_id,
                    dashboard_widgets.c.widget_type == widget_type,
                )
            ).first()

            if existing:
                db_conn.execute(
                    dashboard_widgets.update()
                    .where(dashboard_widgets.c.id == existing.id)
                    .values(config=_json.dumps(cfg), position=position)
                )
                db_conn.commit()
                return _json.dumps({
                    "id": existing.id,
                    "widget_type": widget_type,
                    "position": position,
                    "config": cfg,
                    "action": "updated",
                })
            else:
                result = db_conn.execute(
                    dashboard_widgets.insert().values(
                        user_id=user_id,
                        widget_type=widget_type,
                        position=position,
                        config=_json.dumps(cfg),
                    )
                )
                db_conn.commit()
                return _json.dumps({
                    "id": result.inserted_primary_key[0],
                    "widget_type": widget_type,
                    "position": position,
                    "config": cfg,
                    "action": "created",
                })

        registry.register(
            name="add_dashboard_widget",
            description=(
                "Füge eine Visualisierung zum Dashboard hinzu oder aktualisiere sie. "
                "Nutze dies um dem User Ergebnisse visuell darzustellen — "
                "KPIs, Charts, Tarifvergleiche, Einspar-Übersichten. "
                "Das Widget erscheint sofort auf dem Dashboard während du sprichst. "
                "WICHTIG: Rufe dieses Tool IMMER nach einer Analyse auf, um die Ergebnisse zu visualisieren. "
                "Widget-Typen: invoice_summary (Rechnungsdaten: lieferant, tarif, energiepreis, "
                "grundgebuehr, jahresverbrauch, plz, zaehlpunkt, rechnungsbetrag, zeitraum), "
                "savings_summary, tariff_comparison, consumption_chart, "
                "consumption_kpi, spot_price, battery_sim, pv_sim, "
                "gas_comparison, beg_comparison."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "widget_type": {
                        "type": "string",
                        "description": (
                            "Art des Widgets: invoice_summary, savings_summary, "
                            "tariff_comparison, consumption_chart, consumption_kpi, "
                            "spot_price, battery_sim, pv_sim, gas_comparison, "
                            "beg_comparison"
                        ),
                    },
                    "config": {
                        "type": "object",
                        "description": "Widget-Daten als JSON-Objekt (z.B. {savings_eur: 340, ...})",
                    },
                    "position": {
                        "type": "integer",
                        "description": "Position im Dashboard (0 = oben)",
                        "default": 0,
                    },
                },
                "required": ["widget_type", "config"],
            },
            handler=_add_dashboard_widget,
        )

        registry.register(
            name="get_user_file",
            description=(
                "Lade eine zuvor hochgeladene Datei des Users anhand der Datei-ID. "
                "Gibt den Dateiinhalt zurück (CSV/Excel als Text, PDF als extrahierter Text). "
                "Nutze dies um auf gespeicherte Lastprofile, Rechnungen etc. zuzugreifen "
                "ohne dass der User sie erneut hochladen muss. "
                "Die verfügbaren Dateien und ihre IDs stehen im System-Prompt."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "integer",
                        "description": "ID der gespeicherten Datei (aus der Dateiliste im System-Prompt)",
                    },
                },
                "required": ["file_id"],
            },
            handler=_get_user_file,
        )

    return registry


def build_core_registry(
    user_id: int | None = None,
    db_conn: Any | None = None,
    llm_provider: Any | None = None,
) -> ToolRegistry:
    """Registry mit nur den Kern-Tools für die fokussierte User Journey.

    Aktive Tools: parse_invoice, compare_tariffs, generate_savings_report,
    update_user_memory, get_user_file, add_dashboard_widget.
    """
    full = build_default_registry(
        user_id=user_id, db_conn=db_conn, llm_provider=llm_provider,
    )

    core_tools = {
        "parse_invoice",
        "compare_tariffs",
        "generate_savings_report",
        "update_user_memory",
        "get_user_file",
        "add_dashboard_widget",
    }

    registry = ToolRegistry()
    for name in core_tools:
        if name in full._definitions and name in full._handlers:
            registry._definitions[name] = full._definitions[name]
            registry._handlers[name] = full._handlers[name]

    return registry
