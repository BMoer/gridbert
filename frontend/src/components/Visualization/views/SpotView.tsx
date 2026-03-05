import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Dedicated dashboard for spot tariff analysis. */
export function SpotView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Spot-Tarif-Analyse" subtitle="Gridbert analysiert Spotpreise..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = widget.config;

  const metrics: { label: string; value: string; unit: string; color?: string }[] = [
    ...(config.spot_cost_eur != null ? [{ label: "Spot-Kosten", value: Number(config.spot_cost_eur).toFixed(0), unit: "€/Jahr" }] : []),
    ...(config.fix_cost_eur != null ? [{ label: "Fix-Tarif-Kosten", value: Number(config.fix_cost_eur).toFixed(0), unit: "€/Jahr" }] : []),
    ...(config.savings_eur != null ? [{
      label: "Ersparnis mit Spot",
      value: Number(config.savings_eur).toFixed(0),
      unit: "€/Jahr",
      color: Number(config.savings_eur) > 0 ? "var(--gruen)" : "var(--terracotta)",
    }] : []),
    ...(config.profile_factor_pct != null ? [{ label: "Profil-Kostenfaktor", value: Number(config.profile_factor_pct).toFixed(1), unit: "%" }] : []),
  ];

  return (
    <div>
      <ViewHeader title="Spot-Tarif-Analyse" subtitle="Dynamischer vs. fixer Stromtarif" />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "1rem",
          marginTop: "1.25rem",
        }}
      >
        {metrics.map((m) => (
          <div key={m.label} className="card" style={{ padding: "1rem" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              {m.label}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: m.color ?? "var(--ink)" }}>
              {m.value}
              <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)", marginLeft: "0.2rem" }}>{m.unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
