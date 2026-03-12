import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useChatStore, type ToolActivity } from "../../stores/chatStore";
import { useDashboardStore } from "../../stores/dashboardStore";
import { useChat } from "../../hooks/useChat";
import { useAuthStore } from "../../stores/authStore";
import { getSetupStatus } from "../../api/client";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ApiKeySetupModal } from "../Settings/ApiKeySetupModal";

/** Human-readable tool labels for progress strip. */
const TOOL_LABELS: Record<string, string> = {
  parse_invoice: "Rechnung analysieren",
  compare_tariffs: "Stromtarife vergleichen",
  generate_savings_report: "Einspar-Report erstellen",
  update_user_memory: "Information merken",
  add_dashboard_widget: "Dashboard aktualisieren",
  get_user_file: "Datei laden",
};

/** Map task → dashboard route. */
const TASK_ROUTES: { label: string; widgetTypes: string[]; route: string }[] = [
  { label: "Stromrechnung", widgetTypes: ["invoice_summary"], route: "/dashboard/invoice" },
  { label: "Tarifvergleich", widgetTypes: ["tariff_comparison"], route: "/dashboard/tariff" },
];

function getProgressLabel(): string {
  const messages = useChatStore.getState().messages;
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== "assistant") return "Gridbert arbeitet...";

  if (lastMsg.statusMessage) return lastMsg.statusMessage;

  const running = lastMsg.toolActivity?.filter((a: ToolActivity) => a.status === "running");
  if (running && running.length > 0) {
    return TOOL_LABELS[running[running.length - 1].tool] ?? running[running.length - 1].tool;
  }

  const done = lastMsg.toolActivity?.filter((a: ToolActivity) => a.status === "done") ?? [];
  if (done.length > 0) {
    return `${done.length} ${done.length === 1 ? "Schritt" : "Schritte"} erledigt...`;
  }

  return "Gridbert arbeitet...";
}

/**
 * Full-screen chat page with task sidebar.
 * Primary interface — feels like chatting with Gridbert.
 */
export function ChatPage() {
  const messages = useChatStore((s) => s.messages);
  const isLoading = useChatStore((s) => s.isLoading);
  const { sendMessage, cancelRequest } = useChat();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const widgets = useDashboardStore((s) => s.widgets);
  const userFiles = useDashboardStore((s) => s.userFiles);
  const userMemory = useDashboardStore((s) => s.userMemory);
  const loaded = useDashboardStore((s) => s.loaded);
  const loadAll = useDashboardStore((s) => s.loadAll);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [canSkipSetup, setCanSkipSetup] = useState(false);

  useEffect(() => {
    if (!loaded) loadAll();
  }, [loaded, loadAll]);

  // Check if user needs to configure an API key
  useEffect(() => {
    getSetupStatus()
      .then((status) => {
        if (status.needs_setup) {
          setShowSetup(true);
          setCanSkipSetup(status.has_server_key);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check file uploads (for task "Stromrechnung" — also check PDF files)
  const hasInvoice = userFiles.some(
    (f) => f.media_type === "application/pdf" || f.file_name.endsWith(".pdf"),
  );
  const progressLabel = isLoading ? getProgressLabel() : "";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {showSetup && (
        <ApiKeySetupModal
          onComplete={() => setShowSetup(false)}
          canSkip={canSkipSetup}
        />
      )}
      {/* Header */}
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
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.75rem",
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--ink)",
          }}
        >
          Grid<span style={{ color: "var(--terracotta)" }}>bert</span>
        </div>
        <div style={{ flex: 1 }} />
        <Link
          to="/settings"
          style={{ color: "var(--warm-grau)", display: "flex", alignItems: "center" }}
          title="Einstellungen"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </Link>
        <span style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", color: "var(--warm-grau)" }}>
          {user?.name || user?.email}
        </span>
        <button
          onClick={logout}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "0.75rem",
            color: "var(--warm-grau)",
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          Abmelden
        </button>
      </header>

      {/* Progress strip when loading */}
      {isLoading && (
        <div
          style={{
            flexShrink: 0,
            background: "var(--kreide)",
            borderBottom: "1px solid var(--warm-grau)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "3px",
              background: "linear-gradient(90deg, transparent 0%, var(--terracotta) 50%, transparent 100%)",
              animation: "progress-slide 1.5s ease-in-out infinite",
            }}
          />
          <style>{`@keyframes progress-slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }`}</style>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.4rem 1.5rem", fontSize: "0.75rem", fontFamily: "var(--font-body)", color: "var(--ink)" }}>
            <span className="h-3 w-3 shrink-0 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
            <span>{progressLabel}</span>
          </div>
        </div>
      )}

      {/* Main content: sidebar + chat */}
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* Task sidebar */}
        <aside
          style={{
            width: "220px",
            flexShrink: 0,
            borderRight: "1px solid var(--warm-grau)",
            background: "var(--kreide)",
            padding: "1rem",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          <div style={{ fontFamily: "var(--font-display)", fontSize: "0.9rem", fontWeight: 600, color: "var(--ink)" }}>
            Deine Schritte
          </div>

          {/* Task items */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
            {TASK_ROUTES.map((task) => {
              const isDone = task.widgetTypes.some((wt) => widgets.some((w) => w.widget_type === wt));
              return (
                <div key={task.route} style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.8rem", lineHeight: 1.4 }}>
                  <svg width="16" height="16" viewBox="0 0 20 20" style={{ flexShrink: 0 }}>
                    <circle cx="10" cy="10" r="8" fill="none" stroke={isDone ? "#4A8B6E" : "#A89B8C"} strokeWidth="1.5" />
                    {isDone && <path d="M6,10 L9,13 L14,7" stroke="#4A8B6E" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />}
                  </svg>
                  {isDone ? (
                    <Link
                      to={task.route}
                      style={{ color: "#4A8B6E", textDecoration: "none", fontFamily: "var(--font-body)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
                    >
                      {task.label} →
                    </Link>
                  ) : (
                    <span style={{ color: "var(--warm-grau)", fontFamily: "var(--font-body)" }}>{task.label}</span>
                  )}
                </div>
              );
            })}
          </div>

          {/* File status */}
          {hasInvoice && (
            <div style={{ fontSize: "0.7rem", color: "var(--warm-grau)", fontFamily: "var(--font-mono)" }}>
              {userFiles.map((f) => (
                <div key={f.id} style={{ marginBottom: "0.15rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {f.file_name}
                </div>
              ))}
            </div>
          )}

          {/* User memory */}
          {userMemory.length > 0 && (
            <div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: "0.8rem", fontWeight: 500, color: "var(--ink)", marginBottom: "0.4rem" }}>
                Was ich weiß
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem" }}>
                {userMemory.slice(0, 8).map((m) => (
                  <span
                    key={m.id}
                    style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", background: "var(--bone)", padding: "0.1rem 0.35rem", borderRadius: "var(--radius-sm)", color: "var(--ink)" }}
                  >
                    {m.fact_key}: {m.fact_value}
                  </span>
                ))}
                {userMemory.length > 8 && (
                  <span style={{ fontSize: "0.65rem", color: "var(--warm-grau)" }}>+{userMemory.length - 8} mehr</span>
                )}
              </div>
            </div>
          )}
        </aside>

        {/* Chat area */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "1rem 1.5rem" }}>
            {messages.length === 0 ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", textAlign: "center", gap: "1rem" }}>
                <svg width="80" height="100" viewBox="0 0 130 160" fill="none" style={{ opacity: 0.75 }}>
                  {/* Body */}
                  <rect x="25" y="30" width="80" height="80" rx="10" stroke="var(--ink)" strokeWidth="2.5" fill="var(--kreide)" />
                  {/* Glasses */}
                  <circle cx="50" cy="62" r="14" stroke="var(--ink)" strokeWidth="2" fill="none" />
                  <circle cx="80" cy="62" r="14" stroke="var(--ink)" strokeWidth="2" fill="none" />
                  <path d="M64,60 Q65,57 66,60" stroke="var(--ink)" strokeWidth="1.5" fill="none" />
                  <line x1="36" y1="60" x2="25" y2="56" stroke="var(--ink)" strokeWidth="1.8" strokeLinecap="round" />
                  <line x1="94" y1="60" x2="105" y2="56" stroke="var(--ink)" strokeWidth="1.8" strokeLinecap="round" />
                  {/* Eyes */}
                  <circle cx="50" cy="60" r="3.5" fill="var(--ink)" />
                  <circle cx="80" cy="60" r="3.5" fill="var(--ink)" />
                  <circle cx="51.5" cy="58.5" r="1.5" fill="var(--kreide)" />
                  <circle cx="81.5" cy="58.5" r="1.5" fill="var(--kreide)" />
                  {/* Cheeks */}
                  <circle cx="42" cy="72" r="5" fill="var(--terracotta)" opacity="0.15" />
                  <circle cx="88" cy="72" r="5" fill="var(--terracotta)" opacity="0.15" />
                  {/* Smile */}
                  <path d="M55,77 Q65,86 75,77" stroke="var(--ink)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                  {/* Bow-tie */}
                  <polygon points="55,112 65,107 65,117" fill="var(--terracotta)" stroke="var(--ink)" strokeWidth="1" />
                  <polygon points="75,112 65,107 65,117" fill="var(--terracotta)" stroke="var(--ink)" strokeWidth="1" />
                  <circle cx="65" cy="112" r="2.5" fill="var(--ink)" />
                  {/* Legs */}
                  <line x1="50" y1="110" x2="45" y2="140" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" />
                  <line x1="80" y1="110" x2="85" y2="140" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" />
                  <line x1="45" y1="140" x2="38" y2="140" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" />
                  <line x1="85" y1="140" x2="92" y2="140" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" />
                </svg>
                <div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem", fontWeight: 600, color: "var(--ink)", marginBottom: "0.3rem" }}>
                    Hallo, ich bin Gridbert.
                  </div>
                  <div style={{ fontFamily: "var(--font-body)", fontSize: "0.9rem", color: "var(--warm-grau)", lineHeight: 1.5 }}>
                    Leg deine Stromrechnung auf den Tisch — ich schau mir das an.
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxWidth: "800px", margin: "0 auto" }}>
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    onSuggestionClick={!isLoading ? sendMessage : undefined}
                  />
                ))}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          {/* Cancel button */}
          {isLoading && (
            <div style={{ display: "flex", justifyContent: "center", padding: "0.25rem 0" }}>
              <button
                type="button"
                onClick={cancelRequest}
                className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors hover:opacity-80"
                style={{ borderColor: "var(--warm-grau)", color: "var(--ink)", background: "var(--kreide)" }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
                  <path d="M2 8a6 6 0 1 1 12 0A6 6 0 0 1 2 8Zm5-3a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H7Z" />
                </svg>
                Abbrechen
              </button>
            </div>
          )}

          {/* Input */}
          <div style={{ maxWidth: "800px", margin: "0 auto", width: "100%" }}>
            <ChatInput onSend={(msg, files) => sendMessage(msg, files)} disabled={isLoading} />
          </div>
        </div>
      </div>
    </div>
  );
}
