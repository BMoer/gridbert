import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getLLMConfig,
  setLLMConfig,
  deleteLLMConfig,
  resetAllData,
  type LLMConfig,
  type ApiError,
} from "../../api/client";
import { useAuthStore } from "../../stores/authStore";
import { useChatStore } from "../../stores/chatStore";
import { useDashboardStore } from "../../stores/dashboardStore";

const PROVIDERS = [
  {
    id: "claude",
    label: "Claude (Anthropic)",
    defaultModel: "claude-haiku-4-5-20251001",
    models: [
      { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (schnell)" },
      { value: "claude-sonnet-4-5-20250514", label: "Claude Sonnet 4.5 (stark)" },
    ],
  },
  {
    id: "openai",
    label: "OpenAI",
    defaultModel: "gpt-4o",
    models: [
      { value: "gpt-4o", label: "GPT-4o (stark)" },
      { value: "gpt-4o-mini", label: "GPT-4o Mini (schnell)" },
    ],
  },
] as const;

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);

  // Form state
  const [provider, setProvider] = useState("claude");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState<string>(PROVIDERS[0].defaultModel);
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedProvider = PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0];

  useEffect(() => {
    getLLMConfig()
      .then((c) => {
        setConfig(c);
        if (c.provider) setProvider(c.provider);
        if (c.model) setModel(c.model);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function handleProviderChange(id: string) {
    setProvider(id);
    const p = PROVIDERS.find((x) => x.id === id);
    if (p) setModel(p.defaultModel);
    setError("");
    setSuccess("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("Bitte gib deinen API-Schlüssel ein.");
      return;
    }

    setError("");
    setSuccess("");
    setSaving(true);

    try {
      await setLLMConfig({ provider, api_key: apiKey.trim(), model });
      setApiKey("");
      setConfig({ provider, model, has_key: true });
      setSuccess("Schlüssel gespeichert und verifiziert.");
    } catch (err) {
      setError((err as ApiError)?.message || "Speichern fehlgeschlagen");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setError("");
    setSuccess("");
    setDeleting(true);
    try {
      await deleteLLMConfig();
      setConfig({ provider: "", model: "", has_key: false });
      setApiKey("");
      setSuccess("API-Schlüssel wurde entfernt.");
    } catch (err) {
      setError((err as ApiError)?.message || "Löschen fehlgeschlagen");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
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
        <Link to="/" style={{ textDecoration: "none" }}>
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
        </Link>
        <div style={{ flex: 1 }} />
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

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "2rem 1.5rem" }}>
        <div style={{ maxWidth: "480px", margin: "0 auto" }}>
          <Link
            to="/"
            style={{
              fontFamily: "var(--font-body)",
              fontSize: "0.8rem",
              color: "var(--warm-grau)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              marginBottom: "1.5rem",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Zurück
          </Link>

          <h1 style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", fontWeight: 600, color: "var(--ink)", marginBottom: "1.5rem" }}>
            Einstellungen
          </h1>

          {loading ? (
            <p style={{ fontFamily: "var(--font-body)", color: "var(--warm-grau)" }}>Laden...</p>
          ) : (
            <>
              {/* Current status */}
              {config?.has_key && (
                <div
                  className="card"
                  style={{ marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "0.75rem" }}
                >
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: "var(--gruen)",
                      flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", color: "var(--ink)" }}>
                      <strong>{config.provider === "openai" ? "OpenAI" : "Claude"}</strong>
                      {" · "}
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>{config.model}</span>
                    </div>
                    <div style={{ fontFamily: "var(--font-body)", fontSize: "0.7rem", color: "var(--warm-grau)" }}>
                      API-Schlüssel konfiguriert
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting}
                    style={{
                      fontFamily: "var(--font-body)",
                      fontSize: "0.75rem",
                      color: "var(--fehler)",
                      background: "none",
                      border: "1px solid var(--fehler)",
                      borderRadius: "var(--radius-sm)",
                      padding: "0.25rem 0.5rem",
                      cursor: deleting ? "wait" : "pointer",
                      opacity: deleting ? 0.5 : 1,
                    }}
                  >
                    {deleting ? "..." : "Entfernen"}
                  </button>
                </div>
              )}

              {/* Config form */}
              <form
                onSubmit={handleSubmit}
                className="card"
                style={{ padding: "1.25rem" }}
              >
                <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 600, color: "var(--ink)", marginBottom: "1rem" }}>
                  {config?.has_key ? "Schlüssel ändern" : "API-Schlüssel einrichten"}
                </h2>

                {error && (
                  <p
                    className="rounded px-3 py-2 text-sm"
                    style={{ background: "rgba(184,58,58,0.1)", color: "var(--fehler)", marginBottom: "1rem" }}
                  >
                    {error}
                  </p>
                )}

                {success && (
                  <p
                    className="rounded px-3 py-2 text-sm"
                    style={{ background: "rgba(74,139,110,0.1)", color: "var(--gruen)", marginBottom: "1rem" }}
                  >
                    {success}
                  </p>
                )}

                {/* Provider selector */}
                <div style={{ marginBottom: "1rem" }}>
                  <label className="mb-1.5 block text-sm font-medium" style={{ color: "var(--ink)" }}>Anbieter</label>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    {PROVIDERS.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleProviderChange(p.id)}
                        style={{
                          flex: 1,
                          padding: "0.5rem",
                          borderRadius: "var(--radius-md)",
                          border: provider === p.id ? "2px solid var(--terracotta)" : "1.5px solid var(--warm-grau)",
                          background: provider === p.id ? "rgba(196, 101, 74, 0.06)" : "var(--kreide)",
                          cursor: "pointer",
                          textAlign: "center",
                          fontFamily: "var(--font-body)",
                          fontSize: "0.85rem",
                          fontWeight: 600,
                          color: "var(--ink)",
                          transition: "all 0.15s ease",
                        }}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* API key */}
                <div style={{ marginBottom: "1rem" }}>
                  <label className="mb-1 block text-sm font-medium" style={{ color: "var(--ink)" }}>API-Schlüssel</label>
                  <div style={{ position: "relative" }}>
                    <input
                      type={showKey ? "text" : "password"}
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder={config?.has_key ? "Neuer Schlüssel (leer = behalten)" : provider === "claude" ? "sk-ant-..." : "sk-..."}
                      className="w-full rounded-lg border px-3 py-2 pr-10 focus:outline-none"
                      style={{
                        borderColor: "var(--warm-grau)",
                        background: "var(--kreide)",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.85rem",
                      }}
                      onFocus={(e) => {
                        e.currentTarget.style.borderColor = "var(--terracotta)";
                        e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)";
                      }}
                      onBlur={(e) => {
                        e.currentTarget.style.borderColor = "var(--warm-grau)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      style={{
                        position: "absolute",
                        right: "0.5rem",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        color: "var(--warm-grau)",
                        padding: "0.25rem",
                      }}
                      tabIndex={-1}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        {showKey ? (
                          <>
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                            <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </>
                        ) : (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </>
                        )}
                      </svg>
                    </button>
                  </div>
                </div>

                {/* Model */}
                <div style={{ marginBottom: "1.25rem" }}>
                  <label className="mb-1 block text-sm font-medium" style={{ color: "var(--ink)" }}>Modell</label>
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full rounded-lg border px-3 py-2 focus:outline-none"
                    style={{
                      borderColor: "var(--warm-grau)",
                      background: "var(--kreide)",
                      fontFamily: "var(--font-body)",
                      fontSize: "0.85rem",
                      color: "var(--ink)",
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = "var(--terracotta)";
                      e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)";
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = "var(--warm-grau)";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  >
                    {selectedProvider.models.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={saving || !apiKey.trim()}
                  className="w-full rounded-lg px-4 py-2 font-medium text-white disabled:opacity-50"
                  style={{ background: "var(--terracotta)", cursor: saving ? "wait" : "pointer" }}
                >
                  {saving ? "Wird geprüft..." : "Speichern"}
                </button>
              </form>

              {/* Debug: Reset all data */}
              <div
                style={{
                  marginTop: "2rem",
                  padding: "1rem",
                  borderRadius: "var(--radius-md)",
                  border: "1.5px dashed var(--fehler)",
                  opacity: 0.7,
                }}
              >
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--fehler)", marginBottom: "0.5rem" }}>
                  DEBUG
                </div>
                <p style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--ink)", marginBottom: "0.75rem", lineHeight: 1.4 }}>
                  Alle Gespräche, Dateien, Merkliste, Dashboard-Widgets und API-Schlüssel löschen. Dein Account bleibt bestehen.
                </p>
                <button
                  type="button"
                  onClick={async () => {
                    if (!window.confirm("Wirklich ALLE Daten löschen? Das kann nicht rückgängig gemacht werden.")) return;
                    try {
                      await resetAllData();
                      setConfig({ provider: "", model: "", has_key: false });
                      setApiKey("");
                      useChatStore.getState().reset();
                      useDashboardStore.setState({ widgets: [], userFiles: [], userMemory: [], loaded: false });
                      setSuccess("Alle Daten wurden gelöscht.");
                      setError("");
                    } catch (err) {
                      setError((err as ApiError)?.message || "Reset fehlgeschlagen");
                    }
                  }}
                  className="rounded-lg px-4 py-1.5 text-sm font-medium"
                  style={{
                    color: "white",
                    background: "var(--fehler)",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  Alle Daten zurücksetzen
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
