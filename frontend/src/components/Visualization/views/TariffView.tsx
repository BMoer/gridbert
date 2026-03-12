import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  tariffWidget?: Widget;
  savingsWidget?: Widget;
}

/** Dedicated dashboard for tariff comparison results. */
export function TariffView({ tariffWidget, savingsWidget }: Props) {
  if (!tariffWidget && !savingsWidget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Tarifvergleich" subtitle="Gridbert vergleicht Tarife..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = tariffWidget?.config ?? {};

  // Accept both English and German field names
  const currentCost = (config.current_cost_eur ?? config.aktuelle_kosten_eur) as number | undefined;
  const bestCost = (config.best_cost_eur ?? config.beste_kosten_eur ?? config.bester_tarif_kosten_eur) as number | undefined;
  const savingsEur = savingsWidget?.config?.savings_eur
    ?? savingsWidget?.config?.max_ersparnis_eur
    ?? config.savings_eur
    ?? config.max_ersparnis_eur
    ?? config.ersparnis_eur;
  const tariffs = (config.tariffs ?? config.alternativen ?? config.tarife ?? []) as Record<string, unknown>[];

  return (
    <div>
      <ViewHeader title="Tarifvergleich" subtitle="Deine Optionen im Überblick" />

      {/* Summary KPIs */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "1rem",
          marginTop: "1.25rem",
        }}
      >
        {currentCost != null && (
          <div className="card" style={{ padding: "1rem" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              Aktuelle Kosten
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: "var(--ink)" }}>
              {Number(currentCost).toFixed(0)} <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)" }}>€/Jahr</span>
            </div>
          </div>
        )}
        {bestCost != null && (
          <div className="card" style={{ padding: "1rem" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              Bester Tarif
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: "var(--gruen)" }}>
              {Number(bestCost).toFixed(0)} <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)" }}>€/Jahr</span>
            </div>
          </div>
        )}
        {savingsEur != null && (
          <div className="card" style={{ padding: "1rem", borderLeft: "3px solid var(--gruen)" }}>
            <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", marginBottom: "0.25rem" }}>
              Ersparnis
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: "var(--gruen)" }}>
              {Number(savingsEur).toFixed(0)} <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)" }}>€/Jahr</span>
            </div>
          </div>
        )}
      </div>

      {/* Tariff comparison table */}
      {tariffs.length > 0 && (
        <div className="card" style={{ marginTop: "1.25rem", padding: "1rem", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-body)", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1.5px solid var(--ink)" }}>
                <th style={{ textAlign: "left", padding: "0.5rem", fontWeight: 600 }}>Lieferant</th>
                <th style={{ textAlign: "left", padding: "0.5rem", fontWeight: 600 }}>Tarif</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Gesamtkosten</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Energiepreis</th>
              </tr>
            </thead>
            <tbody>
              {tariffs.map((t, i) => {
                const name = (t.lieferant ?? t.anbieter ?? "—") as string;
                const tarif = (t.tarif ?? t.tarif_name ?? "—") as string;
                const cost = (t.preis_eur ?? t.jahreskosten_eur) as number | undefined;
                const energy = (t.energiepreis_ct ?? t.energiepreis_ct_kwh) as number | undefined;

                return (
                  <tr
                    key={i}
                    style={{
                      borderBottom: "1px solid var(--bone)",
                      background: i === 0 ? "rgba(74,139,110,0.06)" : undefined,
                    }}
                  >
                    <td style={{ padding: "0.5rem", fontWeight: i === 0 ? 600 : 400 }}>{name}</td>
                    <td style={{ padding: "0.5rem" }}>{tarif}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {cost != null ? `${Number(cost).toFixed(0)} €` : "—"}
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {energy != null ? `${Number(energy).toFixed(2)} Ct` : "—"}
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
