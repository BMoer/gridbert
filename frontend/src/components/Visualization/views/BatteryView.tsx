import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface BatteryScenario {
  capacity_kwh?: number;
  price_eur?: number;
  savings_eur?: number;
  amortization_years?: number;
  performance_kwh?: number;
  self_consumption_pct?: number;
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

  const scenarios = (widget.config.scenarios ?? []) as BatteryScenario[];
  const bestIdx = widget.config.best_idx as number | undefined;

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
        {scenarios.map((s, i) => (
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
              {s.capacity_kwh ?? "?"} kWh
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", fontSize: "0.85rem" }}>
              {s.price_eur != null && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--warm-grau)" }}>Investition</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{s.price_eur.toLocaleString("de-AT")} €</span>
                </div>
              )}
              {s.savings_eur != null && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--warm-grau)" }}>Ersparnis/Jahr</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500, color: "var(--gruen)" }}>{s.savings_eur.toFixed(0)} €</span>
                </div>
              )}
              {s.amortization_years != null && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--warm-grau)" }}>Amortisation</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{s.amortization_years.toFixed(1)} Jahre</span>
                </div>
              )}
              {s.self_consumption_pct != null && (
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--warm-grau)" }}>Eigenverbrauch</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{s.self_consumption_pct.toFixed(0)}%</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
