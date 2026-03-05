import { type FormEvent, useState } from "react";
import { setLLMConfig, type ApiError } from "../../api/client";

const PROVIDERS = [
  {
    id: "claude",
    label: "Claude (Anthropic)",
    hint: "console.anthropic.com",
    defaultModel: "claude-haiku-4-5-20251001",
    models: [
      { value: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (schnell)" },
      { value: "claude-sonnet-4-5-20250514", label: "Claude Sonnet 4.5 (stark)" },
    ],
  },
  {
    id: "openai",
    label: "OpenAI",
    hint: "platform.openai.com",
    defaultModel: "gpt-4o",
    models: [
      { value: "gpt-4o", label: "GPT-4o (stark)" },
      { value: "gpt-4o-mini", label: "GPT-4o Mini (schnell)" },
    ],
  },
] as const;

interface Props {
  onComplete: () => void;
  canSkip: boolean;
}

export function ApiKeySetupModal({ onComplete, canSkip }: Props) {
  const [provider, setProvider] = useState<string>("claude");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState<string>(PROVIDERS[0].defaultModel);
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const selectedProvider = PROVIDERS.find((p) => p.id === provider) ?? PROVIDERS[0];

  function handleProviderChange(id: string) {
    setProvider(id);
    const p = PROVIDERS.find((x) => x.id === id);
    if (p) setModel(p.defaultModel);
    setError("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("Bitte gib deinen API-Schlüssel ein.");
      return;
    }

    setError("");
    setSaving(true);

    try {
      await setLLMConfig({ provider, api_key: apiKey.trim(), model });
      onComplete();
    } catch (err) {
      const msg = (err as ApiError)?.message || "Speichern fehlgeschlagen";
      setError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(44, 44, 44, 0.4)",
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "440px",
          margin: "1rem",
          background: "var(--kreide)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-floating)",
          animation: "fadeInUp 0.3s ease-out",
        }}
      >
        {/* Header */}
        <div style={{ padding: "1.5rem 1.5rem 0" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem" }}>
            <svg width="32" height="32" viewBox="0 0 130 130" style={{ flexShrink: 0 }}>
              <circle cx="65" cy="55" r="35" fill="var(--kreide)" stroke="var(--ink)" strokeWidth="2" />
              <circle cx="55" cy="48" r="4" fill="var(--ink)" />
              <circle cx="75" cy="48" r="4" fill="var(--ink)" />
              <path d="M52,62 Q65,72 78,62" stroke="var(--ink)" strokeWidth="2" fill="none" strokeLinecap="round" />
              <rect x="50" y="38" width="12" height="6" rx="2" fill="none" stroke="var(--ink)" strokeWidth="1.5" />
              <rect x="68" y="38" width="12" height="6" rx="2" fill="none" stroke="var(--ink)" strokeWidth="1.5" />
            </svg>
            <div>
              <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem", fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                LLM-Zugang einrichten
              </h2>
              <p style={{ fontFamily: "var(--font-body)", fontSize: "0.8rem", color: "var(--warm-grau)", margin: 0 }}>
                Ich brauche einen API-Schlüssel, damit ich dir helfen kann.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "1rem 1.5rem 1.5rem" }}>
          {error && (
            <p
              className="rounded px-3 py-2 text-sm"
              style={{ background: "rgba(184,58,58,0.1)", color: "var(--fehler)", marginBottom: "1rem" }}
            >
              {error}
            </p>
          )}

          {/* Provider selector */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              className="mb-1.5 block text-sm font-medium"
              style={{ color: "var(--ink)", fontFamily: "var(--font-body)" }}
            >
              Anbieter
            </label>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleProviderChange(p.id)}
                  style={{
                    flex: 1,
                    padding: "0.6rem",
                    borderRadius: "var(--radius-md)",
                    border: provider === p.id ? "2px solid var(--terracotta)" : "1.5px solid var(--warm-grau)",
                    background: provider === p.id ? "rgba(196, 101, 74, 0.06)" : "var(--kreide)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontFamily: "var(--font-body)", fontSize: "0.85rem", fontWeight: 600, color: "var(--ink)" }}>
                    {p.label}
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--warm-grau)", marginTop: "0.15rem" }}>
                    {p.hint}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* API key input */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              className="mb-1 block text-sm font-medium"
              style={{ color: "var(--ink)", fontFamily: "var(--font-body)" }}
            >
              API-Schlüssel
            </label>
            <div style={{ position: "relative" }}>
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={provider === "claude" ? "sk-ant-..." : "sk-..."}
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

          {/* Model selector */}
          <div style={{ marginBottom: "1.25rem" }}>
            <label
              className="mb-1 block text-sm font-medium"
              style={{ color: "var(--ink)", fontFamily: "var(--font-body)" }}
            >
              Modell
            </label>
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

          {/* Buttons */}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {canSkip && (
              <button
                type="button"
                onClick={onComplete}
                className="rounded-lg px-4 py-2 text-sm font-medium"
                style={{
                  color: "var(--warm-grau)",
                  background: "none",
                  border: "1.5px solid var(--warm-grau)",
                  cursor: "pointer",
                }}
              >
                Überspringen
              </button>
            )}
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-lg px-4 py-2 font-medium text-white disabled:opacity-50"
              style={{ background: "var(--terracotta)", cursor: saving ? "wait" : "pointer" }}
            >
              {saving ? "Wird geprüft..." : "Speichern"}
            </button>
          </div>

          {/* Help text */}
          <p style={{ fontFamily: "var(--font-body)", fontSize: "0.7rem", color: "var(--warm-grau)", marginTop: "0.75rem", lineHeight: 1.4 }}>
            Dein Schlüssel wird verschlüsselt gespeichert und nie im Klartext angezeigt.
          </p>
        </form>
      </div>
    </div>
  );
}
