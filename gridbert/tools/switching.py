# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Wechsel-Dokumente — vorausgefüllte PDFs für Tarifwechsel und BEG-Beitritt."""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from gridbert.models import BEGCalculation, Invoice, Tariff

log = logging.getLogger(__name__)


class _GridbertPDF(FPDF):
    """PDF mit Gridbert-Branding."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(22, 163, 74)  # green-dark
        self.cell(0, 8, "Gridbert - Dein Energie-Agent", align="R")
        self.ln(12)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f"Erstellt am {datetime.now(tz=timezone.utc).strftime('%d.%m.%Y')} | Alle Preise brutto inkl. 20% MwSt.", align="C")


def _add_section(pdf: _GridbertPDF, title: str) -> None:
    """Abschnitts-Überschrift."""
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, title)
    pdf.ln(8)
    pdf.set_draw_color(34, 197, 94)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 180, pdf.get_y())
    pdf.ln(4)


def _add_field(pdf: _GridbertPDF, label: str, value: str) -> None:
    """Label + Wert auf einer Zeile."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(55, 7, label)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7, value)
    pdf.ln(7)


def generate_switching_pdf(
    invoice: Invoice,
    target_tariff: Tariff,
    profile: dict | None = None,
) -> Path:
    """Tarifwechsel-Vollmacht als PDF generieren."""
    profile = profile or {}

    pdf = _GridbertPDF()
    pdf.add_page()

    # Titel
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "Vollmacht zum Lieferantenwechsel")
    pdf.ln(16)

    # Auftraggeber
    _add_section(pdf, "Auftraggeber")
    _add_field(pdf, "Name:", profile.get("name", "____________________________"))
    _add_field(pdf, "Adresse:", profile.get("adresse", "____________________________"))
    _add_field(pdf, "PLZ / Ort:", invoice.plz or profile.get("plz", "________"))
    _add_field(pdf, "Zaehlpunkt:", invoice.zaehlpunkt or "AT00____________________________")
    pdf.ln(4)

    # Aktueller Lieferant
    _add_section(pdf, "Aktueller Lieferant")
    _add_field(pdf, "Lieferant:", invoice.lieferant)
    _add_field(pdf, "Tarif:", invoice.tarif_name or "—")
    _add_field(pdf, "Energiepreis:", f"{invoice.energiepreis_ct_kwh:.2f} ct/kWh")
    _add_field(pdf, "Grundgebuehr:", f"{invoice.grundgebuehr_eur_monat:.2f} EUR/Monat")
    pdf.ln(4)

    # Neuer Lieferant
    _add_section(pdf, "Neuer Lieferant")
    _add_field(pdf, "Lieferant:", target_tariff.lieferant)
    _add_field(pdf, "Tarif:", target_tariff.tarif_name)
    _add_field(pdf, "Energiepreis:", f"{target_tariff.energiepreis_ct_kwh:.2f} ct/kWh")
    _add_field(pdf, "Grundgebuehr:", f"{target_tariff.grundgebuehr_eur_monat:.2f} EUR/Monat")
    _add_field(pdf, "Jahreskosten:", f"{target_tariff.jahreskosten_eur:.2f} EUR/Jahr")
    oeko = "Ja" if target_tariff.ist_oekostrom else "Nein"
    _add_field(pdf, "Oekostrom:", oeko)
    pdf.ln(4)

    # Ersparnis
    ersparnis = (
        invoice.energiepreis_ct_kwh * invoice.jahresverbrauch_kwh / 100
        + invoice.grundgebuehr_eur_monat * 12
    ) - target_tariff.jahreskosten_eur
    if ersparnis > 0:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(22, 163, 74)
        pdf.cell(0, 8, f"Geschaetzte Ersparnis: {ersparnis:.2f} EUR/Jahr")
        pdf.ln(12)

    # Vollmachts-Text
    _add_section(pdf, "Vollmacht")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 5,
        "Hiermit beauftrage und bevollmaechtige ich den oben genannten neuen Lieferanten, "
        "alle erforderlichen Schritte fuer den Lieferantenwechsel durchzufuehren, insbesondere "
        "die Kuendigung meines bestehenden Liefervertrages und die Anmeldung beim Netzbetreiber.\n\n"
        "Der Wechsel erfolgt zum naechstmoeglichen Zeitpunkt. Die Netzkosten werden weiterhin "
        "vom zustaendigen Netzbetreiber verrechnet und aendern sich durch den Wechsel nicht.\n\n"
        "Diese Vollmacht kann jederzeit schriftlich widerrufen werden."
    )
    pdf.ln(12)

    # Unterschrift
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(55, 7, "Datum:")
    pdf.cell(0, 7, "____________________")
    pdf.ln(12)
    pdf.cell(55, 7, "Unterschrift:")
    pdf.cell(0, 7, "____________________")

    # Speichern
    tmpdir = tempfile.mkdtemp(prefix="gridbert_pdf_")
    out_path = Path(tmpdir) / "tarifwechsel_vollmacht.pdf"
    pdf.output(str(out_path))
    log.info("Wechsel-PDF erstellt: %s", out_path)
    return out_path


def generate_beg_joining_pdf(
    invoice: Invoice,
    beg: BEGCalculation,
    profile: dict | None = None,
    netzbetreiber: str = "",
) -> Path:
    """BEG-Beitritts-Checkliste als PDF generieren."""
    profile = profile or {}

    pdf = _GridbertPDF()
    pdf.add_page()

    # Titel
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, f"Beitritt: {beg.beg_name}")
    pdf.ln(16)

    # Deine Daten
    _add_section(pdf, "Deine Daten")
    _add_field(pdf, "Name:", profile.get("name", "____________________________"))
    _add_field(pdf, "PLZ / Ort:", invoice.plz or profile.get("plz", "________"))
    _add_field(pdf, "Zaehlpunkt:", invoice.zaehlpunkt or "AT00____________________________")
    _add_field(pdf, "Netzbetreiber:", netzbetreiber or profile.get("netzbetreiber", "—"))
    _add_field(pdf, "Akt. Lieferant:", invoice.lieferant)
    pdf.ln(4)

    # BEG-Details
    _add_section(pdf, "Energiegemeinschaft")
    _add_field(pdf, "Name:", beg.beg_name)
    _add_field(pdf, "Website:", beg.beg_url)
    _add_field(pdf, "BEG-Preis:", f"{beg.beg_preis_ct_kwh:.2f} ct/kWh")
    _add_field(pdf, "Dein akt. Preis:", f"{beg.aktueller_preis_ct_kwh:.2f} ct/kWh")
    _add_field(pdf, "Versorgungsanteil:", f"{beg.versorgungsanteil * 100:.0f}%")
    if beg.einmalkosten_eur > 0:
        _add_field(pdf, "Einmalkosten:", f"{beg.einmalkosten_eur:.0f} EUR")
    pdf.ln(2)

    # Ersparnis
    if beg.ersparnis_jahr_eur > 0:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(22, 163, 74)
        pdf.cell(0, 8, f"Geschaetzte Ersparnis: {beg.ersparnis_jahr_eur:.2f} EUR/Jahr")
        pdf.ln(12)

    # Checkliste
    _add_section(pdf, "Beitritts-Checkliste")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)

    steps = [
        f"[ ] Online-Registrierung auf {beg.beg_url}",
        f"[ ] Datenfreigabe beim Netzbetreiber ({netzbetreiber or '?'}) aktivieren",
        f"[ ] Zaehlpunkt {invoice.zaehlpunkt or 'AT00...'} bei {beg.beg_name} hinterlegen",
        "[ ] Bestaetigung der Zuweisung abwarten (kann einige Wochen dauern)",
        "[ ] Bisherigen Stromlieferant als Reststromlieferant beibehalten",
    ]
    for step in steps:
        pdf.cell(0, 7, step)
        pdf.ln(7)
    pdf.ln(6)

    # Hinweis
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 5,
        "Hinweis: Der Beitritt zu einer Energiegemeinschaft ersetzt NICHT deinen "
        "Stromlieferanten. Du behaeltst deinen bisherigen Vertrag und beziehst "
        "zusaetzlich guenstigeren Strom aus der BEG. Der BEG-Anteil wird direkt "
        "mit deinem Verbrauch verrechnet."
    )
    if beg.notiz:
        pdf.ln(4)
        pdf.multi_cell(0, 5, f"Info: {beg.notiz}")

    # Speichern
    tmpdir = tempfile.mkdtemp(prefix="gridbert_pdf_")
    out_path = Path(tmpdir) / "beg_beitritt.pdf"
    pdf.output(str(out_path))
    log.info("BEG-PDF erstellt: %s", out_path)
    return out_path
