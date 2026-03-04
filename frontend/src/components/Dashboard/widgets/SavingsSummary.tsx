import type { WidgetProps } from "../WidgetRegistry";

export function SavingsSummary({ config }: WidgetProps) {
  const savings = (config.savings_eur as number) ?? 0;
  const description = (config.description as string) ?? "Jährliches Sparpotenzial";

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
      <h3 className="text-sm font-medium text-gray-500">{description}</h3>
      <p className="mt-2 text-3xl font-bold text-gridbert-600">
        {savings > 0 ? `${savings.toFixed(0)} €` : "—"}
      </p>
      <p className="mt-1 text-xs text-gray-400">pro Jahr</p>
    </div>
  );
}
