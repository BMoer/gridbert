import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Dedicated dashboard for BEG (Bürgerenergiegemeinschaft) comparison. */
export function BEGView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Energiegemeinschaften" subtitle="Gridbert vergleicht BEG-Optionen..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = widget.config;
  const providers = (config.providers ?? []) as { name?: string; preis_ct?: number; ersparnis_eur?: number; region?: string }[];

  return (
    <div>
      <ViewHeader title="Energiegemeinschaften" subtitle="BEG-Optionen in deiner Nähe" />

      {providers.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: "1rem",
            marginTop: "1.25rem",
          }}
        >
          {providers.map((p, i) => (
            <div key={i} className="card" style={{ padding: "1.25rem" }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 600, color: "var(--ink)", marginBottom: "0.5rem" }}>
                {p.name ?? `BEG ${i + 1}`}
              </div>
              {p.region && (
                <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.5rem" }}>
                  {p.region}
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", fontSize: "0.85rem" }}>
                {p.preis_ct != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Energiepreis</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{p.preis_ct.toFixed(2)} Ct/kWh</span>
                  </div>
                )}
                {p.ersparnis_eur != null && (
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--warm-grau)" }}>Ersparnis</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500, color: "var(--gruen)" }}>{p.ersparnis_eur.toFixed(0)} €/Jahr</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
