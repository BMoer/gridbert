interface Props {
  config: Record<string, unknown>;
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: "Eingereicht", color: "var(--terracotta)" },
  in_progress: { label: "In Bearbeitung", color: "var(--ink)" },
  completed: { label: "Abgeschlossen", color: "#4A8B6E" },
  cancelled: { label: "Storniert", color: "var(--warm-grau)" },
};

export function SwitchingStatusCard({ config }: Props) {
  const status = String(config.status || "pending");
  const { label, color } = STATUS_MAP[status] ?? STATUS_MAP.pending;
  const targetLieferant = String(config.target_lieferant || "—");
  const targetTarif = String(config.target_tarif || "");
  const savingsEur = Number(config.savings_eur || 0);

  return (
    <div className="card" style={{ gridArea: "switching" }}>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1rem",
          fontWeight: 500,
          marginBottom: "0.85rem",
          color: "var(--ink)",
        }}
      >
        Tarifwechsel
      </div>

      {/* Status badge */}
      <div
        style={{
          display: "inline-block",
          padding: "4px 12px",
          borderRadius: "var(--radius-full, 999px)",
          border: `1.5px solid ${color}`,
          color,
          fontFamily: "var(--font-data)",
          fontSize: "0.8rem",
          fontWeight: 600,
          marginBottom: "0.75rem",
        }}
      >
        {label}
      </div>

      {/* Details */}
      <div style={{ fontSize: "0.9rem", lineHeight: 1.6 }}>
        <div style={{ color: "var(--warm-grau)", fontSize: "0.8rem" }}>Neuer Anbieter</div>
        <div style={{ fontWeight: 600, marginBottom: "0.4rem" }}>
          {targetLieferant}
          {targetTarif && (
            <span style={{ fontWeight: 400, color: "var(--warm-grau)", marginLeft: "0.5rem" }}>
              {targetTarif}
            </span>
          )}
        </div>

        {savingsEur > 0 && (
          <>
            <div style={{ color: "var(--warm-grau)", fontSize: "0.8rem" }}>Ersparnis</div>
            <div
              style={{
                fontFamily: "var(--font-data)",
                fontSize: "1.1rem",
                fontWeight: 600,
                color: "#4A8B6E",
              }}
            >
              {Math.round(savingsEur)} €/Jahr
            </div>
          </>
        )}
      </div>

      {status === "pending" && (
        <div
          style={{
            marginTop: "0.75rem",
            fontSize: "0.8rem",
            color: "var(--warm-grau)",
            lineHeight: 1.5,
          }}
        >
          Ben kümmert sich in den nächsten Tagen um deinen Wechsel.
        </div>
      )}
      {status === "completed" && (
        <div
          style={{
            marginTop: "0.75rem",
            fontSize: "0.8rem",
            color: "#4A8B6E",
            lineHeight: 1.5,
          }}
        >
          Dein Wechsel ist abgeschlossen! Die Kündigung beim alten Anbieter erfolgt automatisch.
        </div>
      )}
    </div>
  );
}
