import { useEffect } from "react";
import { useDashboardStore } from "../../stores/dashboardStore";
import { KPICard } from "./KPICard";
import { ChartArea } from "./ChartArea";
import { GridbertArea } from "./GridbertArea";
import { TaskList } from "./TaskList";
import { QuestionArea } from "./QuestionArea";
import { NewsArea } from "./NewsArea";
import { DocumentTable } from "./DocumentTable";

interface Props {
  onOpenChat: () => void;
}

export function Dashboard({ onOpenChat }: Props) {
  const { loadAll, loaded, widgets } = useDashboardStore();

  useEffect(() => {
    if (!loaded) loadAll();
  }, [loaded, loadAll]);

  // Extract widget data
  const consumptionKpi = widgets.find((w) => w.widget_type === "consumption_kpi");
  const savingsWidget = widgets.find((w) => w.widget_type === "savings_summary");
  const chartWidget = widgets.find((w) => w.widget_type === "consumption_chart");

  const hasKpis = Boolean(consumptionKpi || savingsWidget);
  const hasChart = Boolean(chartWidget);
  const hasDataRow = hasKpis || hasChart;

  // Dynamic grid layout depending on available data
  const gridTemplateAreas = hasDataRow
    ? `
      ${hasKpis && hasChart ? '"kpi1  chart    gridbert"' : ""}
      ${hasKpis && hasChart ? '"kpi2  chart    gridbert"' : ""}
      ${hasKpis && !hasChart ? '"kpi1  gridbert gridbert"' : ""}
      ${hasKpis && !hasChart ? '"kpi2  gridbert gridbert"' : ""}
      ${!hasKpis && hasChart ? '"chart chart    gridbert"' : ""}
      "tasks question news"
      "table table    table"
    `
    : `
      "gridbert gridbert gridbert"
      "tasks   question news"
      "table   table    table"
    `;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gridTemplateRows: "auto auto auto",
        gap: "1.25rem",
        gridTemplateAreas,
      }}
      className="dashboard-grid"
    >
      {/* KPI 1 — only when data exists */}
      {consumptionKpi && (
        <KPICard
          gridArea="kpi1"
          label="Jahresverbrauch"
          value={String(consumptionKpi.config.value ?? "—")}
          unit={String(consumptionKpi.config.unit ?? "kWh")}
          trend={
            consumptionKpi.config.trend_percent
              ? {
                  percent: `${consumptionKpi.config.trend_percent}% ggü. Vorjahr`,
                  direction: Number(consumptionKpi.config.trend_percent) < 0 ? "down" : "up",
                }
              : undefined
          }
          tooltipText="Dein Jahresverbrauch kommt aus dem Lastgang, den du hochgeladen hast."
        />
      )}

      {/* KPI 2 — only when data exists */}
      {savingsWidget && (
        <KPICard
          gridArea="kpi2"
          label="Ersparnis"
          value={String(savingsWidget.config.savings_eur ?? "—")}
          unit="€/Jahr"
          trend={
            savingsWidget.config.savings_eur
              ? { percent: `${savingsWidget.config.savings_eur}€ möglich`, direction: "down" }
              : undefined
          }
          tooltipText="Deine mögliche Ersparnis basiert auf dem Tarifvergleich."
        />
      )}

      {/* Chart — only when load profile data exists */}
      {hasChart && <ChartArea widget={chartWidget!} />}

      <GridbertArea onOpenChat={onOpenChat} />
      <TaskList onOpenChat={onOpenChat} />
      <QuestionArea onOpenChat={onOpenChat} />
      <NewsArea />
      <DocumentTable />
    </div>
  );
}
