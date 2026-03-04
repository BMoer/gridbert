import { useState } from "react";
import type { ChatMessage, ToolActivity } from "../../stores/chatStore";

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-gridbert-500 text-white"
            : "bg-white text-gray-800 shadow-sm border border-gray-100"
        }`}
      >
        {/* Tool activity indicators */}
        {message.toolActivity && message.toolActivity.length > 0 && (
          <div className="mb-2 space-y-1.5">
            {message.toolActivity.map((activity, i) => (
              <ToolIndicator key={i} activity={activity} />
            ))}
          </div>
        )}

        {/* Message text */}
        {message.content && (
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {message.content}
          </div>
        )}

        {/* Streaming cursor */}
        {message.isStreaming && !message.content && !message.toolActivity?.length && (
          <div className="flex space-x-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400 [animation-delay:0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400 [animation-delay:0.2s]" />
          </div>
        )}
      </div>
    </div>
  );
}

/** Human-readable tool labels. */
const TOOL_LABELS: Record<string, string> = {
  parse_invoice: "Rechnung analysieren",
  fetch_smart_meter_data: "Smart Meter Daten laden",
  list_smart_meter_providers: "Netzbetreiber auflisten",
  compare_tariffs: "Stromtarife vergleichen",
  compare_beg_options: "BEG Optionen prüfen",
  compare_gas_tariffs: "Gastarife vergleichen",
  generate_savings_report: "Einsparungs-Report erstellen",
  analyze_load_profile: "Lastprofil analysieren",
  analyze_spot_tariff: "Spot-Tarif analysieren",
  simulate_battery: "Batteriespeicher simulieren",
  simulate_pv: "PV-Anlage simulieren",
  monitor_energy_news: "Energie-News prüfen",
  update_user_memory: "Information merken",
  add_dashboard_widget: "Dashboard aktualisieren",
};

/** Build a short context line from tool input params. */
function describeInput(tool: string, input?: Record<string, unknown>): string | null {
  if (!input) return null;

  switch (tool) {
    case "fetch_smart_meter_data": {
      const parts: string[] = [];
      if (input.provider) parts.push(`Netzbetreiber: ${input.provider}`);
      if (input.date_from && input.date_to)
        parts.push(`Zeitraum: ${input.date_from} – ${input.date_to}`);
      else if (input.date_from) parts.push(`Ab: ${input.date_from}`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "compare_tariffs":
    case "compare_gas_tariffs": {
      const parts: string[] = [];
      if (input.plz) parts.push(`PLZ ${input.plz}`);
      if (input.verbrauch_kwh) parts.push(`${input.verbrauch_kwh} kWh/Jahr`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "compare_beg_options": {
      const parts: string[] = [];
      if (input.plz) parts.push(`PLZ ${input.plz}`);
      if (input.verbrauch_kwh) parts.push(`${input.verbrauch_kwh} kWh/Jahr`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "simulate_pv": {
      const parts: string[] = [];
      if (input.plz) parts.push(`PLZ ${input.plz}`);
      if (input.kwp) parts.push(`${input.kwp} kWp`);
      if (input.orientation) parts.push(`${input.orientation}`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "simulate_battery": {
      if (input.scenarios) return `${(input.scenarios as unknown[]).length} Szenarien`;
      return null;
    }
    case "analyze_load_profile": {
      if (input.data_points) return `${(input.data_points as unknown[]).length} Datenpunkte`;
      return null;
    }
    case "parse_invoice":
      return input.file_name ? `Datei: ${input.file_name}` : null;
    case "update_user_memory":
      return input.fact_key ? `${input.fact_key}` : null;
    default:
      return null;
  }
}

function ToolIndicator({ activity }: { activity: ToolActivity }) {
  const [expanded, setExpanded] = useState(false);
  const isRunning = activity.status === "running";
  const label = TOOL_LABELS[activity.tool] ?? activity.tool;
  const inputDesc = describeInput(activity.tool, activity.input);
  const hasSummary = activity.summary && activity.status === "done";

  return (
    <div className="rounded-lg border border-gridbert-100 bg-gridbert-50/70 text-xs text-gridbert-800">
      {/* Header row — always visible */}
      <button
        type="button"
        onClick={() => hasSummary && setExpanded(!expanded)}
        className={`flex w-full items-center gap-2 px-3 py-1.5 ${hasSummary ? "cursor-pointer hover:bg-gridbert-50" : "cursor-default"}`}
      >
        {/* Status icon */}
        {isRunning ? (
          <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-gridbert-300 border-t-gridbert-600" />
        ) : (
          <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-gridbert-500 text-[9px] text-white">
            &#10003;
          </span>
        )}

        {/* Label + context */}
        <span className="flex-1 text-left">
          <span className="font-medium">{label}</span>
          {inputDesc && (
            <span className="ml-1.5 text-gridbert-500">{inputDesc}</span>
          )}
        </span>

        {/* Expand chevron (only if summary exists) */}
        {hasSummary && (
          <span className={`text-gridbert-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
            &#9662;
          </span>
        )}
      </button>

      {/* Expanded summary */}
      {expanded && hasSummary && (
        <div className="border-t border-gridbert-100 px-3 py-2 text-gridbert-600">
          <pre className="whitespace-pre-wrap font-sans">{activity.summary}</pre>
        </div>
      )}
    </div>
  );
}
