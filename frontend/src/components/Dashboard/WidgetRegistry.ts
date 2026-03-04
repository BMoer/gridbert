import type { ComponentType } from "react";
import { SavingsSummary } from "./widgets/SavingsSummary";
import { TariffComparison } from "./widgets/TariffComparison";
import { ConsumptionChart } from "./widgets/ConsumptionChart";

export interface WidgetProps {
  config: Record<string, unknown>;
}

const registry: Record<string, ComponentType<WidgetProps>> = {
  savings_summary: SavingsSummary,
  tariff_comparison: TariffComparison,
  consumption_chart: ConsumptionChart,
};

export function getWidgetComponent(
  widgetType: string,
): ComponentType<WidgetProps> | null {
  return registry[widgetType] ?? null;
}

export function getWidgetLabel(widgetType: string): string {
  const labels: Record<string, string> = {
    savings_summary: "Ersparnis",
    tariff_comparison: "Tarifvergleich",
    consumption_chart: "Verbrauch",
    heatmap: "Heatmap",
    duration_curve: "Jahresdauerlinie",
    anomaly: "Anomalien",
    spot_price: "Spotpreise",
    baseload_gauge: "Grundlast",
  };
  return labels[widgetType] ?? widgetType;
}
