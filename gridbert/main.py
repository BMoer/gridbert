# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""CLI Entry Point für Gridbert — Deterministische Pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable

import httpx

from gridbert.config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_VISION_MODEL,
    WIENER_NETZE_EMAIL,
    WIENER_NETZE_PASSWORD,
)
from gridbert.models import SavingsReport
from gridbert.report import generate_report
from gridbert.tools.beg_advisor import compare_beg_options
from gridbert.tools.invoice_parser import parse_invoice
from gridbert.tools.smartmeter import fetch_smart_meter_data
from gridbert.tools.tariff_compare import compare_tariffs

log = logging.getLogger(__name__)

# Type alias für Progress-Callback: (step_id, status, message)
ProgressCallback = Callable[[str, str, str], None] | None


def _check_ollama() -> None:
    """Prüfe ob Ollama läuft und die benötigten Models vorhanden sind."""
    try:
        resp = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
    except httpx.ConnectError:
        print(
            f"❌ Ollama ist nicht erreichbar unter {OLLAMA_HOST}\n"
            f"   Starte Ollama mit: ollama serve",
            file=sys.stderr,
        )
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"❌ Ollama antwortet nicht richtig: {e}", file=sys.stderr)
        sys.exit(1)

    # Verfügbare Models: sowohl "qwen2.5:7b" als auch "qwen2.5" matchen
    raw_names = [m["name"] for m in resp.json().get("models", [])]
    available = set(raw_names) | {n.split(":")[0] for n in raw_names}
    missing = []
    for model in (OLLAMA_MODEL, OLLAMA_VISION_MODEL):
        if model not in available and model.split(":")[0] not in available:
            missing.append(model)

    if missing:
        print(
            f"❌ Fehlende Ollama-Models: {', '.join(missing)}\n"
            f"   Installiere mit:",
            file=sys.stderr,
        )
        for m in missing:
            print(f"     ollama pull {m}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Ollama läuft — Models: {OLLAMA_MODEL}, {OLLAMA_VISION_MODEL}")


def _progress(on_progress: ProgressCallback, step_id: str, status: str, message: str) -> None:
    """Fortschritt melden — entweder Callback oder print()."""
    if on_progress:
        on_progress(step_id, status, message)
    else:
        print(message)


def run_pipeline(
    rechnung_path: Path,
    wn_email: str = "",
    wn_password: str = "",
    on_progress: ProgressCallback = None,
) -> tuple[str, int | None]:
    """Deterministische Pipeline: Rechnung → Smart Meter → Tarife → BEG → Report.

    Returns (report_markdown, analysis_id).
    """

    # --- Step 1: Rechnung analysieren ----------------------------------------
    _progress(on_progress, "invoice", "started", "🔍 Analysiere Rechnung...")
    try:
        invoice = parse_invoice(rechnung_path)
        _progress(on_progress, "invoice", "done",
                  f"   ✅ {invoice.lieferant} — {invoice.energiepreis_ct_kwh:.2f} ct/kWh, "
                  f"{invoice.jahresverbrauch_kwh:,.0f} kWh/Jahr")
    except Exception as e:
        _progress(on_progress, "invoice", "error",
                  f"   ❌ Rechnungs-Analyse fehlgeschlagen: {e}")
        raise

    # --- Step 2: Smart Meter (optional) --------------------------------------
    smart_meter = None
    if wn_email and wn_password:
        _progress(on_progress, "smartmeter", "started",
                  "📡 Hole Smart-Meter-Daten von Wiener Netze...")
        try:
            smart_meter = fetch_smart_meter_data(
                email=wn_email,
                password=wn_password,
                zaehlpunkt=invoice.zaehlpunkt,
            )
            _progress(on_progress, "smartmeter", "done",
                      f"   ✅ {len(smart_meter.readings):,} Messwerte, "
                      f"hochgerechnet {smart_meter.jahresverbrauch_kwh:,.0f} kWh/Jahr, "
                      f"Grundlast {smart_meter.grundlast_watt:.0f} W")
        except Exception as e:
            _progress(on_progress, "smartmeter", "error",
                      f"   ⚠️  Smart Meter fehlgeschlagen: {e} — nutze Rechnungsdaten")
    else:
        _progress(on_progress, "smartmeter", "skipped",
                  "📡 Keine Smart-Meter-Credentials — nutze Verbrauch von Rechnung")

    # Bester Verbrauchswert: Smart Meter > Rechnung
    jahresverbrauch = (
        smart_meter.jahresverbrauch_kwh
        if smart_meter and smart_meter.jahresverbrauch_kwh > 0
        else invoice.jahresverbrauch_kwh
    )

    # --- Step 3: Tarifvergleich ----------------------------------------------
    _progress(on_progress, "tariff", "started",
              "📊 Vergleiche Tarife über E-Control...")
    tariff_comparison = None
    try:
        tariff_comparison = compare_tariffs(
            plz=invoice.plz,
            jahresverbrauch_kwh=jahresverbrauch,
            aktueller_lieferant=invoice.lieferant,
            aktueller_energiepreis=invoice.energiepreis_ct_kwh,
            aktuelle_grundgebuehr=invoice.grundgebuehr_eur_monat,
        )
        if tariff_comparison.alternativen:
            best = tariff_comparison.bester_tarif
            _progress(on_progress, "tariff", "done",
                      f"   ✅ {len(tariff_comparison.alternativen)} Alternativen — "
                      f"Bester: {best.lieferant} ({best.tarif_name}), "
                      f"Ersparnis {tariff_comparison.max_ersparnis_eur:,.2f} €/Jahr")
        else:
            _progress(on_progress, "tariff", "done",
                      "   ℹ️  Keine günstigeren Alternativen gefunden")
    except Exception as e:
        _progress(on_progress, "tariff", "error",
                  f"   ⚠️  Tarifvergleich fehlgeschlagen: {e}")

    # --- Step 4: BEG-Vergleich ------------------------------------------------
    _progress(on_progress, "beg", "started",
              "🔋 Vergleiche Energiegemeinschaften...")
    beg_comparison = None
    try:
        beg_comparison = compare_beg_options(
            jahresverbrauch_kwh=jahresverbrauch,
            aktueller_energiepreis_ct_kwh=invoice.energiepreis_ct_kwh,
        )
        if beg_comparison.beste_beg:
            best = beg_comparison.beste_beg
            n_profitable = sum(1 for b in beg_comparison.optionen if b.ersparnis_jahr_eur > 0)
            _progress(on_progress, "beg", "done",
                      f"   ✅ {n_profitable} von {len(beg_comparison.optionen)} BEGs sparen — "
                      f"Beste: {best.beg_name} ({best.ersparnis_jahr_eur:,.2f} €/Jahr)")
        else:
            _progress(on_progress, "beg", "done",
                      "   ℹ️  Keine BEG bringt bei deinem Tarif einen Vorteil")
    except Exception as e:
        _progress(on_progress, "beg", "error",
                  f"   ⚠️  BEG-Vergleich fehlgeschlagen: {e}")

    # --- Step 5: Report generieren + speichern --------------------------------
    _progress(on_progress, "report", "started",
              "📝 Erstelle Einsparungs-Report...")
    report_data = SavingsReport(
        invoice=invoice,
        smart_meter=smart_meter,
        tariff_comparison=tariff_comparison,
        beg_comparison=beg_comparison,
    )
    report = generate_report(report_data)

    # Analyse in SQLite speichern
    analysis_id: int | None = None
    try:
        from gridbert.storage import GridbertStorage
        storage = GridbertStorage()
        analysis_id = storage.save_analysis(report_data, report)
        storage.close()
        log.info("Analyse #%d gespeichert", analysis_id)
    except Exception as e:
        log.warning("Analyse konnte nicht gespeichert werden: %s", e)

    _progress(on_progress, "report", "done", "   ✅ Report fertig!")
    return report, analysis_id


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gridbert",
        description="Gridbert — Dein persönlicher Energie-Agent. Zeig mir was ich spare!",
    )
    parser.add_argument(
        "rechnung",
        nargs="?",
        default=None,
        help="Pfad zur Stromrechnung (PDF oder Bild)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Starte die Browser-Oberfläche statt CLI",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port für die Web-Oberfläche (Standard: 5000)",
    )
    parser.add_argument(
        "--wn-email",
        default=WIENER_NETZE_EMAIL,
        help="Wiener Netze E-Mail (oder WIENER_NETZE_EMAIL in .env)",
    )
    parser.add_argument(
        "--wn-password",
        default=WIENER_NETZE_PASSWORD,
        help="Wiener Netze Passwort (oder WIENER_NETZE_PASSWORD in .env)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Ausführliche Ausgabe (Debug-Logging)",
    )

    args = parser.parse_args()

    # Logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Web-Modus
    if args.web:
        from gridbert.web.app import run_web
        _check_ollama()
        run_web(port=args.port, debug=args.verbose)
        return

    # CLI-Modus: Rechnung ist Pflicht
    if not args.rechnung:
        parser.error("Bitte eine Rechnung angeben oder --web für die Browser-Oberfläche nutzen")

    rechnung_path = Path(args.rechnung)
    if not rechnung_path.exists():
        print(f"Fehler: Datei nicht gefunden: {rechnung_path}", file=sys.stderr)
        sys.exit(1)

    # Ollama-Check
    _check_ollama()

    print("\n⚡ Gridbert startet... Moment, ich schau mir deine Daten an.\n")

    report, _analysis_id = run_pipeline(
        rechnung_path=rechnung_path,
        wn_email=args.wn_email,
        wn_password=args.wn_password,
    )
    print(report)


if __name__ == "__main__":
    main()
