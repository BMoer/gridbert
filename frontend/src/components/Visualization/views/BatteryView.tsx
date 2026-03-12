import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface BatteryScenario {
  capacity_kwh?: number;
  kapazitaet_kwh?: number;
  price_eur?: number;
  preis_eur?: number;
  savings_eur?: number;
  ersparnis_jahr_eur?: number;
  amortization_years?: number;
  amortisation_jahre?: number;
  performance_kwh?: number;
  eigenverbrauch_erhoehung_kwh?: number;
  self_consumption_pct?: number;
  eigenverbrauch_anteil_pct?: number;
}

function v(scenario: BatteryScenario, ...keys: (keyof BatteryScenario)[]): number | undefined {
  for (const k of keys) {
    if (scenario[k] != null) return Number(scenario[k]);
  }
  return undefined;
}

interface Props {
  widget?: Widget;
}

/** Dedicated dashboard for battery simulation results. */
export function BatteryView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Batteriespeicher-Simulation" subtitle="Gridbert berechnet Szenarien..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  // Accept both English and German container field names
  const scenarios = (widget.config.scenarios ?? widget.config.szenarien ?? []) as BatteryScenario[];
  const bestIdx = (widget.config.best_idx ?? widget.config.bestes_szenario_idx) as number | undefined;

  return (
    <div>
      <ViewHeader title="Batteriespeicher-Simulation" subtitle="Szenarien im Vergleich" />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: "1rem",
          marginTop: "1.25rem",
        }}
      >
        {scenarios.map((s, i) => {
          const cap = v(s, "capacity_kwh", "kapazitaet_kwh");
          const price = v(s, "price_eur", "preis_eur");
          const savings = v(s, "savings_eur", "ersparnis_jahr_eur");
          const amort = v(s, "amortization_years", "amortisation_jahre");
          const selfCons = v(s, "self_consumption_pct", "eigenverbrauch_anteil_pct");

          return (
            <div
              key={i}
              className="card"
              style={{
                padding: "1.25rem",
                borderLeft: i === bestIdx ? "3px solid var(--gruen)" : undefined,
                position: "relative",
              }}
            >
              {i === bestIdx && (
                <div
                  style={{
                    position: "absolute",
                    top: "0.5rem",
                    right: "0.5rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.65rem",
                    background: "var(--gruen)",
                    color: "white",
                    padding: "0.1rem 0.4rem",
                    borderRadius: "var(--radius-sm)",
                    fontWeight: 600,
                  }}
                >
                  EMPFOHLEN
                </div>
              )}

              <div style={{ fontFamily: "var(--font-display)", fontSize: "1.1rem", fontWeight: 600, color: "var(--ink)", marginBottom: "0.75rem" }}>
                {cap ?? "?"} kWh
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.85rem" }}>
                {price != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Investition</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{price.toLocaleString("de-AT")} €</span>
                  </div>
                )}
                {savings != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Ersparnis/Jahr</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500, color: "var(--gruen)" }}>{savings.toFixed(0)} €</span>
                  </div>
                )}
                {amort != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Amortisation</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{amort.toFixed(1)} Jahre</span>
                  </div>
                )}
                {selfCons != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Eigenverbrauch</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{selfCons.toFixed(0)}%</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
