import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
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

  const fields: { label: string; value: string | undefined }[] = [
    { label: "Lieferant", value: config.lieferant as string },
    { label: "Tarif", value: config.tarif as string },
    { label: "Energiepreis", value: config.energiepreis ? `${config.energiepreis} Ct/kWh` : undefined },
    { label: "Grundgebühr", value: config.grundgebuehr ? `${config.grundgebuehr} €/Monat` : undefined },
    { label: "Jahresverbrauch", value: config.jahresverbrauch ? `${config.jahresverbrauch} kWh` : undefined },
    { label: "PLZ", value: config.plz as string },
    { label: "Zählpunkt", value: config.zaehlpunkt as string },
    { label: "Rechnungsbetrag", value: config.rechnungsbetrag ? `${config.rechnungsbetrag} €` : undefined },
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
            style={{ padding: "1rem" }}
          >
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              {field.label}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.1rem", fontWeight: 600, color: "var(--ink)" }}>
              {field.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
