import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Strip trailing unit from a value string to avoid duplication (e.g. "33.26 ct/kWh" → "33,26"). */
function stripUnit(val: unknown, ...units: string[]): string | undefined {
  if (val == null) return undefined;
  let s = String(val).trim();
  for (const u of units) {
    // Case-insensitive removal of trailing unit
    const re = new RegExp(`\\s*${u.replace("/", "\\/")}\\s*$`, "i");
    s = s.replace(re, "");
  }
  return s || undefined;
}

/** Dedicated dashboard for invoice analysis results. */
export function InvoiceView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Rechnungsanalyse" subtitle="Gridbert analysiert deine Rechnung..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = widget.config;

  const fields: { label: string; value: string | undefined; mono?: boolean }[] = [
    { label: "Lieferant", value: config.lieferant as string },
    { label: "Tarif", value: config.tarif as string },
    { label: "Energiepreis", value: stripUnit(config.energiepreis, "ct/kwh", "Ct/kWh") ? `${stripUnit(config.energiepreis, "ct/kwh", "Ct/kWh")} Ct/kWh` : undefined },
    { label: "Grundgebühr", value: stripUnit(config.grundgebuehr, "€/monat", "EUR/Monat", "eur/monat") ? `${stripUnit(config.grundgebuehr, "€/monat", "EUR/Monat", "eur/monat")} €/Monat` : undefined },
    { label: "Jahresverbrauch", value: stripUnit(config.jahresverbrauch, "kwh", "kWh") ? `${stripUnit(config.jahresverbrauch, "kwh", "kWh")} kWh` : undefined },
    { label: "PLZ", value: config.plz as string },
    { label: "Zählpunkt", value: config.zaehlpunkt as string, mono: true },
    { label: "Energiekosten", value: stripUnit(config.energiekosten, "€", "EUR", "eur") ? `${stripUnit(config.energiekosten, "€", "EUR", "eur")} €` : undefined },
    { label: "Netzkosten", value: stripUnit(config.netzkosten, "€", "EUR", "eur") ? `${stripUnit(config.netzkosten, "€", "EUR", "eur")} €` : undefined },
    { label: "Rechnungsbetrag", value: stripUnit(config.rechnungsbetrag, "€", "EUR", "eur") ? `${stripUnit(config.rechnungsbetrag, "€", "EUR", "eur")} €` : undefined },
    { label: "Zeitraum", value: config.zeitraum as string },
  ];

  const validFields = fields.filter((f) => f.value);

  return (
    <div>
      <ViewHeader title="Rechnungsanalyse" subtitle="Daten aus deiner Stromrechnung" />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: "1rem",
          marginTop: "1.25rem",
        }}
      >
        {validFields.map((field) => (
          <div
            key={field.label}
            className="card"
            style={{ padding: "1rem", overflow: "hidden" }}
          >
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              {field.label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: field.mono ? "0.85rem" : "1.1rem",
                fontWeight: 600,
                color: "var(--ink)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={field.value}
            >
              {field.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
