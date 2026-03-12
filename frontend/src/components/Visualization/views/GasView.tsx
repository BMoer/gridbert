import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  widget?: Widget;
}

/** Dedicated dashboard for gas tariff comparison. */
export function GasView({ widget }: Props) {
  if (!widget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Gastarif-Vergleich" subtitle="Gridbert vergleicht Gastarife..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = widget.config;
  // Accept both English and German field names
  const tariffs = (config.tariffs ?? config.tarife ?? []) as Record<string, unknown>[];
  const savingsEur = (config.savings_eur ?? config.max_ersparnis_eur ?? config.ersparnis_eur) as number | undefined;

  return (
    <div>
      <ViewHeader title="Gastarif-Vergleich" subtitle="Deine Optionen im Überblick" />

      {savingsEur != null && (
        <div className="card" style={{ padding: "1rem", marginTop: "1.25rem", borderLeft: "3px solid var(--gruen)" }}>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>Ersparnis</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: "var(--gruen)" }}>
            {Number(savingsEur).toFixed(0)} <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)" }}>€/Jahr</span>
          </div>
        </div>
      )}

      {tariffs.length > 0 && (
        <div className="card" style={{ marginTop: "1rem", padding: "1rem", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-body)", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1.5px solid var(--ink)" }}>
                <th style={{ textAlign: "left", padding: "0.5rem", fontWeight: 600 }}>Lieferant</th>
                <th style={{ textAlign: "left", padding: "0.5rem", fontWeight: 600 }}>Tarif</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Kosten</th>
              </tr>
            </thead>
            <tbody>
              {tariffs.map((t, i) => {
                const name = (t.lieferant ?? t.anbieter ?? "—") as string;
                const tarif = (t.tarif ?? t.tarif_name ?? "—") as string;
                const cost = (t.preis_eur ?? t.jahreskosten_eur ?? t.gaspreis_ct_kwh) as number | undefined;
                const isCt = t.gaspreis_ct_kwh != null && t.preis_eur == null && t.jahreskosten_eur == null;

                return (
                  <tr key={i} style={{ borderBottom: "1px solid var(--bone)", background: i === 0 ? "rgba(74,139,110,0.06)" : undefined }}>
                    <td style={{ padding: "0.5rem", fontWeight: i === 0 ? 600 : 400 }}>{name}</td>
                    <td style={{ padding: "0.5rem" }}>{tarif}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {cost != null ? (isCt ? `${Number(cost).toFixed(2)} Ct/kWh` : `${Number(cost).toFixed(0)} €`) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
