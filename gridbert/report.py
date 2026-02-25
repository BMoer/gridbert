# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Report-Generierung in Gridberts Stimme."""

from __future__ import annotations

from gridbert.models import SavingsReport
from gridbert.personality import REPORT_INTRO, REPORT_OUTRO


def generate_report(report: SavingsReport) -> str:
    """Generiere einen Markdown Einsparungs-Report."""
    lines: list[str] = []
    lines.append("# Gridbert Einsparungs-Report")
    lines.append("")
    lines.append(REPORT_INTRO)

    # --- Aktuelle Situation ---
    lines.append("## Deine aktuelle Situation")
    lines.append("")
    inv = report.invoice
    lines.append(f"- **Lieferant:** {inv.lieferant}")
    if inv.tarif_name:
        lines.append(f"- **Tarif:** {inv.tarif_name}")
    lines.append(f"- **Energiepreis:** {inv.energiepreis_ct_kwh:.2f} ct/kWh")
    lines.append(f"- **Grundgebühr:** {inv.grundgebuehr_eur_monat:.2f} €/Monat")
    lines.append(f"- **Jahresverbrauch:** {report.jahresverbrauch_kwh:,.0f} kWh")
    lines.append(f"- **Aktuelle Jahreskosten (Energie + Grundgebühr):** {report.aktuelle_jahreskosten_eur:,.2f} €")

    # Netzkosten (behördlich festgelegt, aus E-Control)
    if report.tariff_comparison and report.tariff_comparison.netzkosten_eur_jahr > 0:
        tc = report.tariff_comparison
        gesamt_inkl_netz = report.aktuelle_jahreskosten_eur + tc.netzkosten_eur_jahr
        lines.append(f"- **Netzkosten:** {tc.netzkosten_eur_jahr:,.2f} €/Jahr ({tc.netzbetreiber}, behördlich festgelegt)")
        lines.append(f"- **Gesamtkosten inkl. Netz:** {gesamt_inkl_netz:,.2f} €/Jahr")
    lines.append("")

    # Smart Meter Details
    if report.smart_meter and report.smart_meter.readings:
        sm = report.smart_meter
        lines.append("### Smart Meter Daten")
        lines.append("")
        lines.append(f"Ich hab {len(sm.readings):,} Messwerte über {sm.tage} Tage ausgewertet.")
        lines.append(f"Dein hochgerechneter Jahresverbrauch: **{sm.jahresverbrauch_kwh:,.0f} kWh**")
        if sm.grundlast_watt > 0:
            lines.append(f"Deine Grundlast: **{sm.grundlast_watt:.0f} Watt** — das ist, was dein Haushalt im Minimum zieht. Immer. Tag und Nacht.")
        lines.append("")

    # --- Tarifvergleich ---
    if report.tariff_comparison:
        tc = report.tariff_comparison
        lines.append("## Tarifvergleich")
        lines.append("")

        if tc.alternativen:
            lines.append(f"Ich hab {len(tc.alternativen)} Tarife für PLZ {tc.plz} gefunden:")
            lines.append("")
            lines.append("| # | Lieferant | Tarif | ct/kWh | Grundgebühr/M | Jahreskosten | Ersparnis |")
            lines.append("|---|-----------|-------|--------|---------------|--------------|-----------|")

            for i, t in enumerate(tc.alternativen, 1):
                ersparnis = tc.aktueller_tarif.jahreskosten_eur - t.jahreskosten_eur
                oeko = " 🌿" if t.ist_oekostrom else ""
                lines.append(
                    f"| {i} | {t.lieferant}{oeko} | {t.tarif_name} | "
                    f"{t.energiepreis_ct_kwh:.2f} | {t.grundgebuehr_eur_monat:.2f} € | "
                    f"{t.jahreskosten_eur:,.2f} € | **{ersparnis:+,.2f} €** |"
                )

            lines.append("")

            best = tc.bester_tarif
            if best and tc.max_ersparnis_eur > 0:
                lines.append(
                    f"Bester Tarif: **{best.lieferant} — {best.tarif_name}** "
                    f"spart dir **{tc.max_ersparnis_eur:,.2f} €/Jahr**. "
                    f"Das sind {tc.max_ersparnis_eur / 12:,.2f} € weniger. Jeden. Einzelnen. Monat."
                )
            elif best:
                lines.append("Dein aktueller Tarif ist schon ziemlich gut. Respekt.")
            lines.append("")
        else:
            lines.append("E-Control Tarifvergleich war leider nicht verfügbar. Versuch's nochmal oder check tarifkalkulator.e-control.at manuell.")
            lines.append("")

    # --- BEG-Vergleich ---
    if report.beg_comparison and report.beg_comparison.optionen:
        bc = report.beg_comparison
        lines.append("## Energiegemeinschaften (BEG)")
        lines.append("")
        lines.append(f"Dein aktueller Energiepreis: **{report.invoice.energiepreis_ct_kwh:.2f} ct/kWh**")
        lines.append("")

        profitable = [b for b in bc.optionen if b.ersparnis_jahr_eur > 0]

        if profitable:
            lines.append("| # | Anbieter | ct/kWh | Anteil | Ersparnis/Jahr | Einmalkosten |")
            lines.append("|---|----------|--------|--------|----------------|--------------|")

            for i, b in enumerate(bc.optionen, 1):
                ersparnis_str = f"**{b.ersparnis_jahr_eur:+,.2f} €**" if b.ersparnis_jahr_eur > 0 else f"{b.ersparnis_jahr_eur:,.2f} €"
                einmal_str = f"{b.einmalkosten_eur:.0f} €" if b.einmalkosten_eur > 0 else "—"
                lines.append(
                    f"| {i} | [{b.beg_name}]({b.beg_url}) | {b.beg_preis_ct_kwh:.2f} | "
                    f"{b.versorgungsanteil * 100:.0f}% | {ersparnis_str} | {einmal_str} |"
                )

            lines.append("")

            best = bc.beste_beg
            if best:
                lines.append(
                    f"Beste Option: **{best.beg_name}** spart dir **{best.ersparnis_jahr_eur:,.2f} €/Jahr** "
                    f"bei {best.versorgungsanteil * 100:.0f}% Versorgungsanteil."
                )
                if best.einmalkosten_eur > 0:
                    lines.append(
                        f"Einmalkosten: {best.einmalkosten_eur:.0f} € — amortisiert sich in "
                        f"**{best.amortisation_monate:.1f} Monaten**."
                    )
        else:
            lines.append("Keine BEG ist bei deinem aktuellen Energiepreis günstiger. Das passiert, wenn dein Tarif schon sehr günstig ist.")
        lines.append("")
    elif report.beg_calculation:
        # Legacy: einzelne BEGCalculation
        beg = report.beg_calculation
        lines.append("## Energiegemeinschaft (BEG)")
        lines.append("")
        lines.append(f"BEG-Strompreis: **{beg.beg_preis_ct_kwh:.2f} ct/kWh** (dein aktueller: {beg.aktueller_preis_ct_kwh:.2f} ct/kWh)")
        if beg.ersparnis_jahr_eur > 0:
            lines.append(f"**Ersparnis: {beg.ersparnis_jahr_eur:,.2f} €/Jahr**")
        lines.append("")

    # --- Gesamtersparnis ---
    lines.append("## Gesamtersparnis")
    lines.append("")

    gesamt = report.gesamtersparnis_eur
    if gesamt > 0:
        lines.append(f"**Du kannst bis zu {gesamt:,.2f} €/Jahr sparen.**")
        lines.append("")
        lines.append(f"Das sind **{gesamt / 12:,.2f} € pro Monat**. Oder anders gesagt: {gesamt / 365:,.2f} € am Tag. Jeden Tag.")
        lines.append(f"In 5 Jahren: **{gesamt * 5:,.2f} €**. Ich sag ja nur.")
    else:
        lines.append("Ehrlich gesagt: Deine aktuelle Situation ist schon ziemlich optimiert. Ich bin beeindruckt.")
    lines.append("")

    # --- Nächste Schritte ---
    lines.append("## Nächste Schritte")
    lines.append("")

    step = 1
    if report.tariff_comparison and report.tariff_comparison.max_ersparnis_eur > 0:
        best = report.tariff_comparison.bester_tarif
        if best:
            lines.append(f"{step}. **Tarifwechsel prüfen** — Wechsel zu {best.lieferant} ({best.tarif_name}). "
                         f"Geht online in 5 Minuten. Dein alter Vertrag wird automatisch gekündigt.")
            step += 1

    best_beg = report._beste_beg
    if best_beg and best_beg.ersparnis_jahr_eur > 0:
        lines.append(f"{step}. **{best_beg.beg_name} beitreten** — Online auf {best_beg.beg_url} anmelden, "
                     f"dann Datenfreigabe beim Netzbetreiber aktivieren.")
        step += 1

    if step == 1:
        lines.append("Nichts zu tun — genieß deinen günstigen Strom!")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(REPORT_OUTRO)

    return "\n".join(lines)
