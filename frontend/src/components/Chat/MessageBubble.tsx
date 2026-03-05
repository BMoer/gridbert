import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, ToolActivity } from "../../stores/chatStore";

/** Small inline Gridbert avatar for assistant messages. */
function ChatAvatar() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      style={{ flexShrink: 0, marginTop: "0.15rem" }}
    >
      <rect x="4" y="4" width="24" height="24" rx="6" stroke="var(--ink)" strokeWidth="1.5" fill="var(--kreide)" />
      <circle cx="12" cy="15" r="3.5" stroke="var(--ink)" strokeWidth="1" fill="none" />
      <circle cx="20" cy="15" r="3.5" stroke="var(--ink)" strokeWidth="1" fill="none" />
      <circle cx="12" cy="14.5" r="1.2" fill="var(--ink)" />
      <circle cx="20" cy="14.5" r="1.2" fill="var(--ink)" />
      <path d="M13,21 Q16,24 19,21" stroke="var(--ink)" strokeWidth="1" fill="none" strokeLinecap="round" />
      <path d="M15.5,14.5 Q16,13 16.5,14.5" stroke="var(--ink)" strokeWidth="0.8" fill="none" />
    </svg>
  );
}

interface Props {
  message: ChatMessage;
  onSuggestionClick?: (text: string) => void;
}

export function MessageBubble({ message, onSuggestionClick }: Props) {
  const isUser = message.role === "user";
  const hasToolActivity = (message.toolActivity?.length ?? 0) > 0;
  const hasRunningTools = message.toolActivity?.some((a) => a.status === "running") ?? false;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`} style={{ gap: "0.5rem" }}>
      {/* Gridbert avatar on assistant messages */}
      {!isUser && <ChatAvatar />}
      <div
        className="max-w-[80%] rounded-2xl px-4 py-3"
        style={
          isUser
            ? { background: "var(--terracotta)", color: "var(--kreide)" }
            : { background: "var(--kreide)", color: "var(--ink)", boxShadow: "var(--shadow-card)" }
        }
      >
        {/* Status message (while agent is thinking, before any content) */}
        {message.isStreaming && message.statusMessage && !message.content && !hasToolActivity && (
          <div className="flex items-center gap-2 text-xs" style={{ color: "var(--warm-grau)" }}>
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
            {message.statusMessage}
          </div>
        )}

        {/* Streaming cursor — only when no content, no tools, no status */}
        {message.isStreaming && !message.content && !hasToolActivity && !message.statusMessage && (
          <div className="flex space-x-1">
            <span className="h-2 w-2 animate-bounce rounded-full" style={{ background: "var(--terracotta)" }} />
            <span className="h-2 w-2 animate-bounce rounded-full [animation-delay:0.1s]" style={{ background: "var(--terracotta)" }} />
            <span className="h-2 w-2 animate-bounce rounded-full [animation-delay:0.2s]" style={{ background: "var(--terracotta)" }} />
          </div>
        )}

        {/* Message text — markdown for assistant, plain for user */}
        {message.content && (
          isUser ? (
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </div>
          ) : (
            <div className="prose prose-sm max-w-none leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_table]:block [&_table]:overflow-x-auto">
              <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
            </div>
          )
        )}

        {/* Tool activity indicators — BELOW text so user sees them after reading */}
        {hasToolActivity && (
          <div className={`space-y-1.5 ${message.content ? "mt-3 pt-3" : ""}`} style={message.content ? { borderTop: "1px solid var(--bone)" } : undefined}>
            {message.toolActivity!.map((activity, i) => (
              <ToolIndicator key={i} activity={activity} />
            ))}
          </div>
        )}

        {/* "Still working" indicator — shown when streaming + has content or tools are done but more turns expected */}
        {message.isStreaming && (message.content || hasToolActivity) && !hasRunningTools && (
          <div className="mt-2 flex items-center gap-2 text-xs" style={{ color: "var(--warm-grau)" }}>
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
            {message.statusMessage || "Gridbert arbeitet noch..."}
          </div>
        )}

        {/* Suggestion chips */}
        {message.suggestions && message.suggestions.length > 0 && !message.isStreaming && onSuggestionClick && (
          <div className="mt-3 flex flex-wrap gap-1.5 pt-3" style={{ borderTop: "1px solid var(--bone)" }}>
            {message.suggestions.map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onSuggestionClick(suggestion)}
                className="rounded-full border px-3 py-1 text-xs transition-colors"
                style={{ background: "var(--kreide)", borderColor: "var(--warm-grau)", color: "var(--ink)" }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; }}
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
    <div className="rounded-lg border text-xs" style={{ borderColor: "var(--warm-grau)", background: "var(--bone)", color: "var(--ink)" }}>
      {/* Header row — always visible */}
      <button
        type="button"
        onClick={() => hasSummary && setExpanded(!expanded)}
        className={`flex w-full items-center gap-2 px-3 py-1.5 ${hasSummary ? "cursor-pointer" : "cursor-default"}`}
      >
        {/* Status icon */}
        {isRunning ? (
          <span className="h-3.5 w-3.5 shrink-0 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
        ) : (
          <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[9px] text-white" style={{ background: "var(--gruen)" }}>
            &#10003;
          </span>
        )}

        {/* Label + context */}
        <span className="flex-1 text-left">
          <span className="font-medium">{label}</span>
          {inputDesc && (
            <span className="ml-1.5" style={{ color: "var(--warm-grau)" }}>{inputDesc}</span>
          )}
        </span>

        {/* Expand chevron (only if summary exists) */}
        {hasSummary && (
          <span className={`transition-transform ${expanded ? "rotate-180" : ""}`} style={{ color: "var(--warm-grau)" }}>
            &#9662;
          </span>
        )}
      </button>

      {/* Expanded summary */}
      {expanded && hasSummary && (
        <div className="px-3 py-2" style={{ borderTop: "1px solid var(--warm-grau)", color: "var(--ink)", opacity: 0.8 }}>
          <pre className="whitespace-pre-wrap font-sans">{activity.summary}</pre>
        </div>
      )}
    </div>
  );
}
