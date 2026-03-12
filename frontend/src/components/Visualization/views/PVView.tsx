import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Pick the first non-null value from config under the given keys. */
function pick(config: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    if (config[key] != null) return Number(config[key]);
  }
  return null;
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

  // Accept both English and German field names (LLM may use either)
  const yieldKwh = pick(config, "yield_kwh", "jahresertrag_kwh");
  const selfConsumption = pick(config, "self_consumption_kwh", "eigenverbrauch_kwh");
  const feedIn = pick(config, "feed_in_kwh", "einspeisung_kwh");
  const investment = pick(config, "investment_eur", "investition_eur");
  const subsidy = pick(config, "subsidy_eur", "foerderung_eur");
  const savings = pick(config, "savings_eur", "ersparnis_jahr_eur", "ersparnis_eur");
  const amortization = pick(config, "amortization_years", "amortisation_jahre");
  const selfConsumptionPct = pick(config, "self_consumption_pct", "eigenverbrauch_anteil_pct");
  const systemKwp = pick(config, "anlage_kwp", "system_kwp");
  const recommendation = config.recommendation ?? config.empfehlung;

  const metrics: { label: string; value: string; unit: string; highlight?: boolean }[] = [
    ...(systemKwp != null ? [{ label: "Anlagengröße", value: String(systemKwp.toFixed(1)), unit: "kWp" }] : []),
    ...(yieldKwh != null ? [{ label: "Jahresertrag", value: String(yieldKwh.toFixed(0)), unit: "kWh" }] : []),
    ...(selfConsumption != null ? [{ label: "Eigenverbrauch", value: String(selfConsumption.toFixed(0)), unit: `kWh${selfConsumptionPct != null ? ` (${selfConsumptionPct.toFixed(0)}%)` : ""}` }] : []),
    ...(feedIn != null ? [{ label: "Einspeisung", value: String(feedIn.toFixed(0)), unit: "kWh" }] : []),
    ...(investment != null ? [{ label: "Investition", value: String(investment.toFixed(0)), unit: "€" }] : []),
    ...(subsidy != null ? [{ label: "Förderung", value: String(subsidy.toFixed(0)), unit: "€", highlight: true }] : []),
    ...(savings != null ? [{ label: "Ersparnis/Jahr", value: String(savings.toFixed(0)), unit: "€", highlight: true }] : []),
    ...(amortization != null ? [{ label: "Amortisation", value: String(amortization.toFixed(1)), unit: "Jahre" }] : []),
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

      {recommendation != null && (
        <div className="card" style={{ marginTop: "1.25rem", padding: "1.25rem", borderLeft: "3px solid var(--solar-gelb)" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "0.9rem", fontWeight: 500, marginBottom: "0.5rem" }}>
            Empfehlung
          </div>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem", color: "var(--ink)", lineHeight: 1.5 }}>
            {String(recommendation)}
          </div>
        </div>
      )}
    </div>
  );
}
