import type { Widget } from "../../../api/client";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  tariffWidget?: Widget;
  savingsWidget?: Widget;
}

/** Try multiple field names, return first truthy value. */
function pick<T>(obj: Record<string, unknown>, ...keys: string[]): T | undefined {
  for (const k of keys) {
    if (obj[k] != null && obj[k] !== "") return obj[k] as T;
  }
  return undefined;
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
  const sConfig = savingsWidget?.config ?? {};

  const currentCost = pick<number>(config, "current_cost_eur", "aktuelle_kosten_eur", "jahreskosten_aktuell");
  const bestCost = pick<number>(config, "best_cost_eur", "beste_kosten_eur", "bester_tarif_kosten_eur", "jahreskosten_best");
  const savingsEur = pick<number>(sConfig, "savings_eur", "max_ersparnis_eur", "ersparnis_eur")
    ?? pick<number>(config, "savings_eur", "max_ersparnis_eur", "ersparnis_eur");
  const netzkosten = pick<number>(config, "netzkosten_eur", "netzkosten");
  const tariffs = (pick<Record<string, unknown>[]>(config, "tariffs", "alternativen", "tarife") ?? []);

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
              Aktuelle Energiekosten
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 600, color: "var(--ink)" }}>
              {Number(currentCost).toFixed(0)} <span style={{ fontSize: "0.85rem", fontWeight: 400, color: "var(--warm-grau)" }}>€/Jahr</span>
            </div>
            {netzkosten != null && (
              <div style={{ fontFamily: "var(--font-body)", fontSize: "0.75rem", color: "var(--warm-grau)", marginTop: "0.25rem" }}>
                + {Number(netzkosten).toFixed(0)} € Netzkosten (fix)
              </div>
            )}
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
                <th style={{ textAlign: "left", padding: "0.5rem", fontWeight: 600 }}>Typ</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Jahreskosten</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Energiepreis</th>
                <th style={{ textAlign: "right", padding: "0.5rem", fontWeight: 600 }}>Ersparnis</th>
              </tr>
            </thead>
            <tbody>
              {tariffs.map((t, i) => {
                const name = pick<string>(t, "lieferant", "anbieter") ?? "—";
                const tarif = pick<string>(t, "tarif", "tarif_name", "name") ?? "—";
                const typ = pick<string>(t, "tariftyp", "typ", "type") ?? "";
                const cost = pick<number>(t, "jahreskosten_eur", "preis_eur", "gesamtkosten_eur", "kosten_eur");
                const energy = pick<number>(t, "energiepreis_ct", "energiepreis_ct_kwh", "ct_kwh");
                const savings = pick<number>(t, "ersparnis_eur", "savings_eur");

                // Color-code tariff type
                const typColor = typ.toLowerCase().includes("fix") ? "var(--gruen)"
                  : typ.toLowerCase().includes("spot") || typ.toLowerCase().includes("stunden") ? "var(--terracotta)"
                  : typ.toLowerCase().includes("float") || typ.toLowerCase().includes("monat") ? "#c49a3f"
                  : "var(--warm-grau)";

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
                    <td style={{ padding: "0.5rem", color: typColor, fontWeight: 600, fontSize: "0.8rem" }}>{typ || "—"}</td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {cost != null ? `${Number(cost).toFixed(0)} €` : "—"}
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)" }}>
                      {energy != null ? `${Number(energy).toFixed(2)} Ct` : "—"}
                    </td>
                    <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "var(--font-mono)", color: savings != null ? "var(--gruen)" : undefined }}>
                      {savings != null ? `${Number(savings).toFixed(0)} €` : "—"}
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
