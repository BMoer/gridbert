import type { Widget } from "../../../api/client";
import { ChartArea } from "../../Dashboard/ChartArea";
import { ViewHeader } from "./shared/ViewHeader";

interface Props {
  kpiWidget?: Widget;
  chartWidget?: Widget;
}

/** Format number with German locale (e.g., 7436.2 → "7.436", 0.42 → "0,42"). */
function formatDE(value: number, decimals?: number): string {
  const d = decimals ?? (value >= 100 ? 0 : value >= 10 ? 1 : 2);
  return value.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
}

interface SavingsItem {
  kategorie: string;
  beschreibung: string;
  einsparung_kwh: number;
  einsparung_eur: number;
  konfidenz: string;
}

const KONFIDENZ_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  high: { bg: "var(--gruen)", color: "#fff", label: "hoch" },
  medium: { bg: "var(--warnung)", color: "#fff", label: "mittel" },
  low: { bg: "var(--warm-grau)", color: "#fff", label: "niedrig" },
};

const KATEGORIE_LABELS: Record<string, string> = {
  base_load: "Grundlast-Reduktion",
  peak_shaving: "Spitzenlast-Glättung",
  weekend: "Wochenend-Optimierung",
  night: "Nacht-Optimierung",
};

/** Build the correct image src from a base64 string (may or may not include data: prefix). */
function imgSrc(base64: string): string {
  return base64.startsWith("data:") ? base64 : `data:image/png;base64,${base64}`;
}

/** Dedicated dashboard for load profile analysis. */
export function LoadProfileView({ kpiWidget, chartWidget }: Props) {
  if (!kpiWidget && !chartWidget) {
    return (
      <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
        <ViewHeader title="Lastprofil-Analyse" subtitle="Gridbert analysiert deinen Verbrauch..." />
        <div className="flex items-center justify-center gap-2 mt-4">
          <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
          <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem" }}>Daten werden verarbeitet</span>
        </div>
      </div>
    );
  }

  const config = kpiWidget?.config ?? {};
  const chartConfig = chartWidget?.config ?? {};

  // Primary KPI metrics (new field names from explicit schema)
  const primaryMetrics: { label: string; value: number; unit: string; decimals?: number }[] = [];
  if (config.total_kwh) primaryMetrics.push({ label: "Jahresverbrauch", value: Number(config.total_kwh), unit: "kWh", decimals: 0 });
  if (config.grundlast_kw) primaryMetrics.push({ label: "Grundlast", value: Number(config.grundlast_kw), unit: "kW" });
  if (config.spitzenlast_kw) primaryMetrics.push({ label: "Spitzenlast", value: Number(config.spitzenlast_kw), unit: "kW" });
  if (config.volllaststunden) primaryMetrics.push({ label: "Volllaststunden", value: Number(config.volllaststunden), unit: "h", decimals: 0 });
  // Legacy fallback: old field names
  if (primaryMetrics.length === 0) {
    if (config.value) primaryMetrics.push({ label: "Jahresverbrauch", value: Number(config.value), unit: String(config.unit ?? "kWh"), decimals: 0 });
    if (config.base_load_kw) primaryMetrics.push({ label: "Grundlast", value: Number(config.base_load_kw), unit: "kW" });
    if (config.peak_kw) primaryMetrics.push({ label: "Spitzenlast", value: Number(config.peak_kw), unit: "kW" });
    if (config.full_load_hours) primaryMetrics.push({ label: "Volllaststunden", value: Number(config.full_load_hours), unit: "h", decimals: 0 });
  }

  // Savings
  const sparpotenzialEur = Number(config.sparpotenzial_eur) || 0;
  const sparpotenzialKwh = Number(config.sparpotenzial_kwh) || 0;
  const einsparpotenziale = (config.einsparpotenziale as SavingsItem[] | undefined) ?? [];

  // Secondary metrics
  const secondaryMetrics: { label: string; value: number; unit: string }[] = [];
  if (config.grundlast_anteil_pct) secondaryMetrics.push({ label: "Grundlast-Anteil", value: Number(config.grundlast_anteil_pct), unit: "%" });
  if (config.nacht_mean_kw) secondaryMetrics.push({ label: "Nachtverbrauch", value: Number(config.nacht_mean_kw), unit: "kW" });
  if (config.wochenende_mean_kw) secondaryMetrics.push({ label: "Wochenend-Verbrauch", value: Number(config.wochenende_mean_kw), unit: "kW" });
  if (config.mean_kw) secondaryMetrics.push({ label: "Durchschnitt", value: Number(config.mean_kw), unit: "kW" });

  // Base64 images — check both chartWidget and kpiWidget (legacy)
  const heatmap = (chartConfig.heatmap_base64 as string | undefined) || (config.heatmap_base64 as string | undefined);
  const durationCurve = (chartConfig.duration_curve_base64 as string | undefined) || (config.duration_curve_base64 as string | undefined);
  const monthlyChartImg = chartConfig.monthly_chart_base64 as string | undefined;

  return (
    <div>
      <ViewHeader title="Lastprofil-Analyse" subtitle="Verbrauchsdaten und Kennzahlen" />

      {/* === Primary KPI Cards (gradient) === */}
      {primaryMetrics.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: "1rem",
            marginTop: "1.25rem",
          }}
        >
          {primaryMetrics.map((m) => (
            <div
              key={m.label}
              style={{
                background: "linear-gradient(135deg, var(--strom-blau), var(--info))",
                borderRadius: "var(--radius-md)",
                padding: "1.25rem",
                boxShadow: "var(--shadow-card)",
                color: "var(--kreide)",
              }}
            >
              <div style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", opacity: 0.85, marginBottom: "0.3rem" }}>
                {m.label}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.75rem", fontWeight: 700, lineHeight: 1.1 }}>
                {formatDE(m.value, m.decimals)}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", opacity: 0.75, marginTop: "0.15rem" }}>
                {m.unit}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* === Savings Highlight Card === */}
      {sparpotenzialEur > 0 && (
        <div
          style={{
            background: "linear-gradient(135deg, var(--gruen), #5EA88A)",
            borderRadius: "var(--radius-md)",
            padding: "1.5rem",
            marginTop: "1.25rem",
            color: "var(--kreide)",
            boxShadow: "var(--shadow-card)",
          }}
        >
          <div style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", opacity: 0.85, marginBottom: "0.25rem" }}>
            Einsparpotenzial
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "2rem", fontWeight: 700 }}>
            ~{formatDE(sparpotenzialEur, 0)} € / Jahr
          </div>
          <div style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", opacity: 0.85, marginTop: "0.25rem" }}>
            Basierend auf {formatDE(sparpotenzialKwh, 0)} kWh möglicher Reduktion
          </div>
        </div>
      )}

      {/* === Monthly Consumption Chart === */}
      {monthlyChartImg ? (
        <div className="card" style={{ padding: "1rem", marginTop: "1.25rem" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, marginBottom: "0.75rem" }}>
            Monatsverbrauch
          </div>
          <img src={imgSrc(monthlyChartImg)} alt="Monatsverbrauch" style={{ width: "100%", borderRadius: "var(--radius-sm)" }} />
        </div>
      ) : chartWidget ? (
        <div style={{ marginTop: "1.25rem" }}>
          <ChartArea widget={chartWidget} />
        </div>
      ) : null}

      {/* === Heatmap + Duration Curve === */}
      {(heatmap || durationCurve) && (
        <div style={{ display: "grid", gridTemplateColumns: heatmap && durationCurve ? "1fr 1fr" : "1fr", gap: "1rem", marginTop: "1.25rem" }}>
          {heatmap && (
            <div className="card" style={{ padding: "1rem" }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.9rem", fontWeight: 500, marginBottom: "0.75rem" }}>Heatmap</div>
              <img src={imgSrc(heatmap)} alt="Lastgang-Heatmap" style={{ width: "100%", borderRadius: "var(--radius-sm)" }} />
            </div>
          )}
          {durationCurve && (
            <div className="card" style={{ padding: "1rem" }}>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.9rem", fontWeight: 500, marginBottom: "0.75rem" }}>Jahresdauerlinie</div>
              <img src={imgSrc(durationCurve)} alt="Jahresdauerlinie" style={{ width: "100%", borderRadius: "var(--radius-sm)" }} />
            </div>
          )}
        </div>
      )}

      {/* === Savings Opportunities Table === */}
      {einsparpotenziale.length > 0 && (
        <div className="card" style={{ padding: 0, marginTop: "1.25rem", overflow: "hidden" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, padding: "1rem 1.25rem 0.5rem" }}>
            Einsparmöglichkeiten
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-body)", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "var(--strom-blau)", color: "#fff" }}>
                <th style={{ padding: "0.6rem 1.25rem", textAlign: "left", fontWeight: 500 }}>Maßnahme</th>
                <th style={{ padding: "0.6rem 1.25rem", textAlign: "right", fontWeight: 500 }}>Einsparung</th>
                <th style={{ padding: "0.6rem 1.25rem", textAlign: "center", fontWeight: 500 }}>Konfidenz</th>
              </tr>
            </thead>
            <tbody>
              {einsparpotenziale.map((item, i) => {
                const konfStyle = KONFIDENZ_STYLES[item.konfidenz] ?? KONFIDENZ_STYLES.low;
                return (
                  <tr
                    key={i}
                    style={{ borderBottom: i < einsparpotenziale.length - 1 ? "1px solid var(--bone)" : "none" }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "var(--kreide)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                  >
                    <td style={{ padding: "0.75rem 1.25rem" }}>
                      <div style={{ fontWeight: 500 }}>{KATEGORIE_LABELS[item.kategorie] ?? item.kategorie}</div>
                      {item.beschreibung && (
                        <div style={{ fontSize: "0.78rem", color: "var(--warm-grau)", marginTop: "0.15rem" }}>{item.beschreibung}</div>
                      )}
                    </td>
                    <td style={{ padding: "0.75rem 1.25rem", textAlign: "right", fontFamily: "var(--font-mono)", whiteSpace: "nowrap" }}>
                      {formatDE(item.einsparung_eur, 0)} € <span style={{ color: "var(--warm-grau)", fontSize: "0.78rem" }}>({formatDE(item.einsparung_kwh, 0)} kWh)</span>
                    </td>
                    <td style={{ padding: "0.75rem 1.25rem", textAlign: "center" }}>
                      <span
                        style={{
                          display: "inline-block",
                          background: konfStyle.bg,
                          color: konfStyle.color,
                          fontSize: "0.7rem",
                          padding: "0.15rem 0.5rem",
                          borderRadius: "var(--radius-full)",
                          fontWeight: 500,
                        }}
                      >
                        {konfStyle.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* === Secondary Metrics === */}
      {secondaryMetrics.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: "0.75rem",
            marginTop: "1.25rem",
          }}
        >
          {secondaryMetrics.map((m) => (
            <div key={m.label} className="card" style={{ padding: "1rem" }}>
              <div style={{ fontFamily: "var(--font-body)", fontSize: "0.78rem", color: "var(--warm-grau)", marginBottom: "0.2rem" }}>
                {m.label}
              </div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.25rem", fontWeight: 600, color: "var(--ink)" }}>
                {formatDE(m.value)}
                <span style={{ fontSize: "0.75rem", fontWeight: 400, color: "var(--warm-grau)", marginLeft: "0.2rem" }}>{m.unit}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
