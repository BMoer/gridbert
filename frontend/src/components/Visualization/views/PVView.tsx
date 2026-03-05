import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Dedicated dashboard for PV/Balkonkraftwerk simulation results. */
export function PVView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="PV-Simulation" subtitle="Gridbert berechnet den Ertrag..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = widget.config;

  const metrics: { label: string; value: string; unit: string; highlight?: boolean }[] = [
    ...(config.yield_kwh != null ? [{ label: "Jahresertrag", value: String(Number(config.yield_kwh).toFixed(0)), unit: "kWh" }] : []),
    ...(config.self_consumption_kwh != null ? [{ label: "Eigenverbrauch", value: String(Number(config.self_consumption_kwh).toFixed(0)), unit: "kWh" }] : []),
    ...(config.feed_in_kwh != null ? [{ label: "Einspeisung", value: String(Number(config.feed_in_kwh).toFixed(0)), unit: "kWh" }] : []),
    ...(config.investment_eur != null ? [{ label: "Investition", value: String(Number(config.investment_eur).toFixed(0)), unit: "€" }] : []),
    ...(config.subsidy_eur != null ? [{ label: "Förderung", value: String(Number(config.subsidy_eur).toFixed(0)), unit: "€", highlight: true }] : []),
    ...(config.savings_eur != null ? [{ label: "Ersparnis/Jahr", value: String(Number(config.savings_eur).toFixed(0)), unit: "€", highlight: true }] : []),
    ...(config.amortization_years != null ? [{ label: "Amortisation", value: String(Number(config.amortization_years).toFixed(1)), unit: "Jahre" }] : []),
  ];

  return (
    <div>
      <ViewHeader title="PV-Simulation" subtitle="Ertrag und Wirtschaftlichkeit deiner Anlage" />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: "1rem",
          marginTop: "1.25rem",
        }}
      >
        {metrics.map((m) => (
          <div
            key={m.label}
            className="card"
            style={{
              padding: "1rem",
              borderLeft: m.highlight ? "3px solid var(--solar-gelb)" : undefined,
            }}
          >
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              {m.label}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: m.highlight ? "var(--gruen)" : "var(--ink)" }}>
              {m.value}
              <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)", marginLeft: "0.2rem" }}>{m.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {config.recommendation != null && (
        <div className="card" style={{ marginTop: "1.25rem", padding: "1.25rem", borderLeft: "3px solid var(--solar-gelb)" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "0.9rem", fontWeight: 500, marginBottom: "0.5rem" }}>
            Empfehlung
          </div>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem", color: "var(--ink)", lineHeight: 1.5 }}>
            {String(config.recommendation)}
          </div>
        </div>
      )}
    </div>
  );
}
