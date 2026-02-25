# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Agent-Loop: LLM + Prompt-basiertes Tool-Calling ohne Framework."""

from __future__ import annotations

import json
import logging
import re

import ollama

from gridbert.config import OLLAMA_HOST, OLLAMA_MODEL
from gridbert.models import SavingsReport
from gridbert.personality import SYSTEM_PROMPT
from gridbert.report import generate_report
from gridbert.tools.beg_advisor import calculate_beg_advantage, get_beitritts_schritte
from gridbert.tools.invoice_parser import parse_invoice
from gridbert.tools.smartmeter import fetch_smart_meter_data
from gridbert.tools.tariff_compare import compare_tariffs

log = logging.getLogger(__name__)

# --- Tool-Dispatcher --------------------------------------------------------

TOOL_PROGRESS = {
    "parse_invoice": "🔍 Analysiere Rechnung...",
    "fetch_smart_meter_data": "📡 Hole Smart-Meter-Daten von Wiener Netze...",
    "compare_tariffs": "📊 Vergleiche Tarife über E-Control...",
    "calculate_beg_advantage": "🔋 Berechne 7Energy BEG-Vorteil...",
    "generate_savings_report": "📝 Erstelle Einsparungs-Report...",
}

VALID_TOOLS = {
    "parse_invoice",
    "fetch_smart_meter_data",
    "compare_tariffs",
    "calculate_beg_advantage",
    "generate_savings_report",
}


def _execute_tool(name: str, args: dict, state: dict) -> str:
    """Führe ein Tool aus und gib das Ergebnis als String zurück."""
    progress = TOOL_PROGRESS.get(name, f"⚙️  {name}...")
    print(progress)
    log.info("Tool aufgerufen: %s(%s)", name, json.dumps(args, ensure_ascii=False)[:200])

    try:
        if name == "parse_invoice":
            invoice = parse_invoice(args["file_path"])
            state["invoice"] = invoice
            return f"Rechnung analysiert:\n{invoice.model_dump_json(indent=2)}"

        elif name == "fetch_smart_meter_data":
            sm_data = fetch_smart_meter_data(
                email=args["email"],
                password=args["password"],
                zaehlpunkt=args.get("zaehlpunkt", ""),
            )
            state["smart_meter"] = sm_data
            return (
                f"Smart Meter Daten geladen: {len(sm_data.readings)} Messwerte, "
                f"{sm_data.tage} Tage, hochgerechneter Jahresverbrauch: "
                f"{sm_data.jahresverbrauch_kwh:,.0f} kWh, "
                f"Grundlast: {sm_data.grundlast_watt:.0f} W"
            )

        elif name == "compare_tariffs":
            # Robuste Argument-Erkennung: LLM variiert Feldnamen
            inv = state.get("invoice")
            comparison = compare_tariffs(
                plz=str(args.get("plz", getattr(inv, "plz", "") if inv else "")),
                jahresverbrauch_kwh=float(args.get("jahresverbrauch_kwh",
                    getattr(inv, "jahresverbrauch_kwh", 0) if inv else 0)),
                aktueller_lieferant=str(args.get("aktueller_lieferant",
                    args.get("lieferant", getattr(inv, "lieferant", "") if inv else ""))),
                aktueller_energiepreis=float(args.get("aktueller_energiepreis",
                    args.get("energiepreis", args.get("energiepreis_ct_kwh",
                    getattr(inv, "energiepreis_ct_kwh", 0) if inv else 0)))),
                aktuelle_grundgebuehr=float(args.get("aktuelle_grundgebuehr",
                    args.get("grundgebuehr", args.get("grundgebuehr_eur_monat",
                    getattr(inv, "grundgebuehr_eur_monat", 0) if inv else 0)))),
            )
            state["tariff_comparison"] = comparison
            if comparison.alternativen:
                best = comparison.bester_tarif
                return (
                    f"Tarifvergleich: {len(comparison.alternativen)} Alternativen gefunden. "
                    f"Bester: {best.lieferant} ({best.tarif_name}) mit "
                    f"{best.jahreskosten_eur:,.2f} €/Jahr. "
                    f"Ersparnis: {comparison.max_ersparnis_eur:,.2f} €/Jahr"
                )
            return "Tarifvergleich: Keine günstigeren Alternativen gefunden."

        elif name == "calculate_beg_advantage":
            inv = state.get("invoice")
            beg = calculate_beg_advantage(
                jahresverbrauch_kwh=float(args.get("jahresverbrauch_kwh",
                    getattr(inv, "jahresverbrauch_kwh", 0) if inv else 0)),
                aktueller_energiepreis_ct_kwh=float(args.get("aktueller_energiepreis_ct_kwh",
                    args.get("energiepreis_ct_kwh", args.get("energiepreis",
                    getattr(inv, "energiepreis_ct_kwh", 0) if inv else 0)))),
            )
            state["beg_calculation"] = beg
            return (
                f"BEG-Vorteil berechnet: {beg.ersparnis_jahr_eur:,.2f} €/Jahr Ersparnis, "
                f"Amortisation in {beg.amortisation_monate:.1f} Monaten"
            )

        elif name == "generate_savings_report":
            if "invoice" not in state:
                return "Fehler: Keine Rechnungsdaten vorhanden. Bitte zuerst parse_invoice aufrufen."
            savings_report = SavingsReport(
                invoice=state["invoice"],
                smart_meter=state.get("smart_meter"),
                tariff_comparison=state.get("tariff_comparison"),
                beg_calculation=state.get("beg_calculation"),
            )
            report_text = generate_report(savings_report)
            state["report"] = report_text
            return f"Report erstellt:\n\n{report_text}"

        else:
            return f"Unbekanntes Tool: {name}"

    except Exception as e:
        log.error("Tool %s fehlgeschlagen: %s", name, e)
        return f"Fehler bei {name}: {e}"


# --- Tool-Call Parsing aus Text ---------------------------------------------

# Flexibel: <tool_call>{...}</tool_call> ODER <tool_name>{...}</tool_name>
_TOOL_NAMES_PATTERN = "|".join(VALID_TOOLS)
_TOOL_CALL_RE = re.compile(
    rf"<(?:tool_call|{_TOOL_NAMES_PATTERN})>\s*(\{{.*?\}})\s*</(?:tool_call|{_TOOL_NAMES_PATTERN})>",
    re.DOTALL,
)
# Cleanup-Pattern für die finale Ausgabe
_TOOL_TAG_CLEANUP_RE = re.compile(
    rf"</?(?:tool_call|{_TOOL_NAMES_PATTERN})>",
)


def _parse_tool_call(content: str) -> tuple[str, dict] | None:
    """Parse einen <tool_call> oder <tool_name> Block aus der LLM-Antwort.

    Returns:
        (tool_name, arguments) oder None wenn kein Tool-Call gefunden.
    """
    match = _TOOL_CALL_RE.search(content)
    if not match:
        return None

    raw = match.group(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Versuche den Tool-Namen trotzdem zu extrahieren
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', raw)
        if name_match and name_match.group(1) in VALID_TOOLS:
            log.warning("Tool-Call JSON ungültig, aber Name erkannt: %s", name_match.group(1))
            return name_match.group(1), {}
        log.warning("Tool-Call JSON ungültig: %s", raw[:200])
        return None

    name = data.get("name", "")
    args = data.get("arguments", data.get("parameters", {}))
    if not isinstance(args, dict):
        args = {}

    if name not in VALID_TOOLS:
        log.warning("Unbekannter Tool-Name: %s", name)
        return None

    return name, args


# --- Agent Loop -------------------------------------------------------------

MAX_TURNS = 15


def run_agent(
    user_message: str,
    state: dict | None = None,
    max_turns: int = MAX_TURNS,
) -> tuple[str, dict]:
    """Führe den Agent-Loop aus.

    Returns:
        (final_response, state) — Die letzte LLM-Antwort und der aktuelle State.
    """
    if state is None:
        state = {}

    client = ollama.Client(host=OLLAMA_HOST, timeout=120)

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for turn in range(max_turns):
        log.info("Agent Turn %d/%d", turn + 1, max_turns)
        if turn == 0:
            print("🤖 Gridbert denkt nach...")

        response = client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
        )

        content = response.message.content or ""
        log.debug("LLM Antwort: %s", content[:300])

        # Tool-Call aus Text parsen
        parsed = _parse_tool_call(content)

        if not parsed:
            # Keine Tool-Calls → Finale Antwort
            # Bereinige etwaige fehlformatierte Tool-Call-Versuche aus der Ausgabe
            clean = _TOOL_TAG_CLEANUP_RE.sub("", content).strip()
            log.info("Agent fertig (keine weiteren Tool-Calls)")
            return clean, state

        fn_name, fn_args = parsed
        log.info("Tool-Call erkannt: %s", fn_name)

        # LLM-Antwort (inkl. Tool-Call) in History speichern
        messages.append({"role": "assistant", "content": content})

        # Tool ausführen
        result = _execute_tool(fn_name, fn_args, state)

        # Tool-Ergebnis als User-Nachricht zurückspeisen
        messages.append({
            "role": "user",
            "content": f"Tool-Ergebnis von {fn_name}:\n\n{result}\n\nFahre mit dem nächsten Schritt fort.",
        })

    # Max turns erreicht
    log.warning("Agent hat max_turns (%d) erreicht", max_turns)
    return "Ich hab zu viele Schritte gebraucht. Hier ist was ich bisher habe:", state
