import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ToolActivity } from "../../stores/chatStore";

interface Props {
  message: ChatMessage;
  onSuggestionClick?: (text: string) => void;
}

export function MessageBubble({ message, onSuggestionClick }: Props) {
  const isUser = message.role === "user";
  const hasToolActivity = (message.toolActivity?.length ?? 0) > 0;
  const hasRunningTools = message.toolActivity?.some((a) => a.status === "running") ?? false;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-gridbert-500 text-white"
            : "bg-white text-gray-800 shadow-sm border border-gray-100"
        }`}
      >
        {/* Status message (while agent is thinking, before any content) */}
        {message.isStreaming && message.statusMessage && !message.content && !hasToolActivity && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-gray-200 border-t-gridbert-500" />
            {message.statusMessage}
          </div>
        )}

        {/* Streaming cursor — only when no content, no tools, no status */}
        {message.isStreaming && !message.content && !hasToolActivity && !message.statusMessage && (
          <div className="flex space-x-1">
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400 [animation-delay:0.1s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-gridbert-400 [animation-delay:0.2s]" />
          </div>
        )}

        {/* Message text — markdown for assistant, plain for user */}
        {message.content && (
          isUser ? (
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </div>
          ) : (
            <div className="prose prose-sm prose-gray max-w-none leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_table]:block [&_table]:overflow-x-auto">
              <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
            </div>
          )
        )}

        {/* Tool activity indicators — BELOW text so user sees them after reading */}
        {hasToolActivity && (
          <div className={`space-y-1.5 ${message.content ? "mt-3 border-t border-gray-100 pt-3" : ""}`}>
            {message.toolActivity!.map((activity, i) => (
              <ToolIndicator key={i} activity={activity} />
            ))}
          </div>
        )}

        {/* "Still working" indicator — shown when streaming + has content or tools are done but more turns expected */}
        {message.isStreaming && (message.content || hasToolActivity) && !hasRunningTools && (
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-gray-200 border-t-gridbert-500" />
            {message.statusMessage || "Gridbert arbeitet noch..."}
          </div>
        )}

        {/* Suggestion chips */}
        {message.suggestions && message.suggestions.length > 0 && !message.isStreaming && onSuggestionClick && (
          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-gray-100 pt-3">
            {message.suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick(suggestion)}
                className="rounded-full border border-gridbert-200 bg-gridbert-50 px-3 py-1 text-xs text-gridbert-700 transition-colors hover:border-gridbert-400 hover:bg-gridbert-100"
              >
                {suggestion}
              </button>
            ))}
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
  get_user_file: "Gespeicherte Datei laden",
  add_dashboard_widget: "Dashboard aktualisieren",
  web_search: "Web-Suche",
};

/** Build a short context line from tool input params. */
function describeInput(tool: string, input?: Record<string, unknown>): string | null {
  if (!input) return null;

  switch (tool) {
    case "fetch_smart_meter_data": {
      const parts: string[] = [];
      if (input.provider_id) parts.push(`${input.provider_id}`);
      if (input.date_from && input.date_to)
        parts.push(`${input.date_from} – ${input.date_to}`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "compare_tariffs":
    case "compare_gas_tariffs": {
      const parts: string[] = [];
      if (input.plz) parts.push(`PLZ ${input.plz}`);
      if (input.jahresverbrauch_kwh) parts.push(`${input.jahresverbrauch_kwh} kWh/Jahr`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "compare_beg_options": {
      const parts: string[] = [];
      if (input.jahresverbrauch_kwh) parts.push(`${input.jahresverbrauch_kwh} kWh/Jahr`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "simulate_pv": {
      const parts: string[] = [];
      if (input.plz) parts.push(`PLZ ${input.plz}`);
      if (input.anlage_kwp) parts.push(`${input.anlage_kwp} kWp`);
      if (input.ausrichtung) parts.push(`${input.ausrichtung}`);
      return parts.length ? parts.join(" · ") : null;
    }
    case "simulate_battery":
      return null;
    case "analyze_load_profile": {
      if (input.csv_text) return "CSV-Daten verarbeiten";
      if (input.consumption_data) return `${(input.consumption_data as unknown[]).length} Datenpunkte`;
      return null;
    }
    case "parse_invoice":
      return input.file_name ? `Datei: ${input.file_name}` : null;
    case "update_user_memory":
      return input.fact_key ? `${input.fact_key}: ${input.fact_value ?? ""}` : null;
    case "get_user_file":
      return input.file_id ? `Datei #${input.file_id}` : null;
    case "web_search":
      return input.query ? `${input.query}` : null;
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
