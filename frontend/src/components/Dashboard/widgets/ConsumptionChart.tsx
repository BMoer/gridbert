import type { WidgetProps } from "../WidgetRegistry";

interface MonthlyData {
  month: string;
  kwh: number;
}

export function ConsumptionChart({ config }: WidgetProps) {
  const data = (config.monthly_data as MonthlyData[]) ?? [];

  if (data.length === 0) {
    return (
      <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
        <h3 className="text-sm font-medium text-gray-500">Verbrauch</h3>
        <p className="mt-3 text-sm text-gray-400">Noch keine Verbrauchsdaten.</p>
      </div>
    );
  }

  const maxKwh = Math.max(...data.map((d) => d.kwh));

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
      <h3 className="text-sm font-medium text-gray-500">Monatsverbrauch</h3>
      <div className="mt-3 flex items-end gap-1" style={{ height: 120 }}>
        {data.map((d, i) => {
          const pct = maxKwh > 0 ? (d.kwh / maxKwh) * 100 : 0;
          return (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-t bg-gridbert-400 transition-all"
                style={{ height: `${pct}%`, minHeight: 2 }}
                title={`${d.kwh} kWh`}
              />
              <span className="text-[10px] text-gray-400">{d.month}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
