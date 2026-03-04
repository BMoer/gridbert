import type { WidgetProps } from "../WidgetRegistry";

interface TariffEntry {
  name: string;
  price_ct: number;
  is_current?: boolean;
}

export function TariffComparison({ config }: WidgetProps) {
  const tariffs = (config.tariffs as TariffEntry[]) ?? [];

  if (tariffs.length === 0) {
    return (
      <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
        <h3 className="text-sm font-medium text-gray-500">Tarifvergleich</h3>
        <p className="mt-3 text-sm text-gray-400">Noch keine Tarifdaten.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
      <h3 className="text-sm font-medium text-gray-500">Tarifvergleich</h3>
      <div className="mt-3 space-y-2">
        {tariffs.slice(0, 5).map((t, i) => (
          <div key={i} className="flex items-center justify-between">
            <span className={`text-sm ${t.is_current ? "font-semibold text-gray-800" : "text-gray-600"}`}>
              {t.name}
              {t.is_current && (
                <span className="ml-1.5 rounded bg-gridbert-100 px-1.5 py-0.5 text-xs text-gridbert-700">
                  aktuell
                </span>
              )}
            </span>
            <span className="text-sm font-medium text-gray-800">
              {t.price_ct.toFixed(2)} ct/kWh
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
