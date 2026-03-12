import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Pick the first non-null numeric value from config. */
function pick(config: Record<string, unknown>, ...keys: string[]): number | null {
  for (const key of keys) {
    if (config[key] != null) return Number(config[key]);
  }
  return null;
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

  // Accept both English and German field names
  const spotCost = pick(config, "spot_cost_eur", "spot_kosten_eur");
  const fixCost = pick(config, "fix_cost_eur", "fix_kosten_eur", "voll_kosten_eur");
  const savings = pick(config, "savings_eur", "ersparnis_vs_fix_eur", "ersparnis_eur");
  const profileFactor = pick(config, "profile_factor_pct", "profilkostenfaktor_pct");

  const metrics: { label: string; value: string; unit: string; color?: string }[] = [
    ...(spotCost != null ? [{ label: "Spot-Kosten", value: spotCost.toFixed(0), unit: "€/Jahr" }] : []),
    ...(fixCost != null ? [{ label: "Fix-Tarif-Kosten", value: fixCost.toFixed(0), unit: "€/Jahr" }] : []),
    ...(savings != null ? [{
      label: "Ersparnis mit Spot",
      value: savings.toFixed(0),
      unit: "€/Jahr",
      color: savings > 0 ? "var(--gruen)" : "var(--terracotta)",
    }] : []),
    ...(profileFactor != null ? [{ label: "Profil-Kostenfaktor", value: profileFactor.toFixed(1), unit: "%" }] : []),
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
