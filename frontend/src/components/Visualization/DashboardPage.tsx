import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useDashboardStore } from "../../stores/dashboardStore";
import { InvoiceView } from "./views/InvoiceView";
import { LoadProfileView } from "./views/LoadProfileView";
import { TariffView } from "./views/TariffView";
import { BatteryView } from "./views/BatteryView";
import { PVView } from "./views/PVView";
import { SpotView } from "./views/SpotView";
import { GasView } from "./views/GasView";
import { BEGView } from "./views/BEGView";

/** Map URL param → page title. */
const VIEW_TITLES: Record<string, string> = {
  invoice: "Stromrechnung",
  load_profile: "Lastprofil-Analyse",
  tariff: "Tarifvergleich",
  battery: "Speicher-Simulation",
  pv: "PV-Anlage",
  spot: "Spot-Tarif",
  gas: "Gastarife",
  beg: "Energiegemeinschaft",
};

/**
 * Full-screen dashboard drill-down page.
 * Renders the appropriate view based on the URL param.
 */
export function DashboardPage() {
  const { view } = useParams<{ view: string }>();
  const widgets = useDashboardStore((s) => s.widgets);
  const loaded = useDashboardStore((s) => s.loaded);
  const loadAll = useDashboardStore((s) => s.loadAll);

  useEffect(() => {
    if (!loaded) loadAll();
  }, [loaded, loadAll]);

  const title = VIEW_TITLES[view ?? ""] ?? "Dashboard";

  const findWidget = (type: string) => widgets.find((w) => w.widget_type === type);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Header with back navigation */}
      <header
        className="sketch-border-bottom"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          padding: "0.75rem 1.5rem",
          flexShrink: 0,
        }}
      >
        <Link
          to="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            color: "var(--ink)",
            textDecoration: "none",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--terracotta)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--ink)"; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10.5 3L5.5 8l5 5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Zurück zum Chat
        </Link>
        <div style={{ flex: 1 }} />
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.1rem",
            fontWeight: 600,
            color: "var(--ink)",
          }}
        >
          {title}
        </div>
        <div style={{ flex: 1 }} />
        {/* Spacer for centering the title */}
        <div style={{ width: "120px" }} />
      </header>

      {/* View content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem 2rem" }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
          {!loaded ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "3rem", gap: "0.5rem" }}>
              <span className="h-4 w-4 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
              <span style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem", color: "var(--warm-grau)" }}>Daten laden...</span>
            </div>
          ) : (
            renderView(view, findWidget)
          )}
        </div>
      </div>
    </div>
  );
}

function renderView(
  view: string | undefined,
  findWidget: (type: string) => ReturnType<typeof useDashboardStore.getState>["widgets"][number] | undefined,
) {
  switch (view) {
    case "invoice":
      return <InvoiceView widget={findWidget("invoice_summary")} />;
    case "load_profile":
      return (
        <LoadProfileView
          kpiWidget={findWidget("consumption_kpi")}
          chartWidget={findWidget("consumption_chart")}
        />
      );
    case "tariff":
      return (
        <TariffView
          tariffWidget={findWidget("tariff_comparison")}
          savingsWidget={findWidget("savings_summary")}
        />
      );
    case "battery":
      return <BatteryView widget={findWidget("battery_sim")} />;
    case "pv":
      return <PVView widget={findWidget("pv_sim")} />;
    case "spot":
      return <SpotView widget={findWidget("spot_price")} />;
    case "gas":
      return <GasView widget={findWidget("gas_comparison")} />;
    case "beg":
      return <BEGView widget={findWidget("beg_comparison")} />;
    default:
      return (
        <div style={{ textAlign: "center", padding: "3rem", color: "var(--warm-grau)" }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem", marginBottom: "0.5rem" }}>
            Ansicht nicht gefunden
          </div>
          <Link to="/" style={{ color: "var(--terracotta)" }}>Zurück zum Chat</Link>
        </div>
      );
  }
}
