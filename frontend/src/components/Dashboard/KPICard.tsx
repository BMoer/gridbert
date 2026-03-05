import { useState } from "react";

interface Props {
  gridArea: string;
  label: string;
  value: string;
  unit: string;
  trend?: { percent: string; direction: "up" | "down" };
  tooltipText?: string;
}

export function KPICard({ gridArea, label, value, unit, trend, tooltipText }: Props) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="card" style={{ gridArea }}>
      <div
        style={{
          fontFamily: "var(--font-body)",
          fontSize: "0.875rem",
          color: "var(--warm-grau)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "0.5rem",
        }}
      >
        {label}
        {tooltipText && (
          <button
            onClick={() => setShowTooltip(!showTooltip)}
            aria-label="Info"
            style={{
              width: 20,
              height: 20,
              borderRadius: "var(--radius-full)",
              border: "1.5px solid var(--terracotta)",
              color: "var(--terracotta)",
              fontFamily: "var(--font-body)",
              fontSize: "0.7rem",
              fontStyle: "italic",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              background: "transparent",
              lineHeight: 1,
              transition: "background 0.2s, color 0.2s",
            }}
          >
            i
          </button>
        )}
      </div>

      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "2rem",
          fontWeight: 600,
          color: "var(--ink)",
          lineHeight: 1.1,
        }}
      >
        {value}
        <span
          style={{
            fontSize: "1rem",
            fontWeight: 400,
            color: "var(--warm-grau)",
            marginLeft: "0.25rem",
          }}
        >
          {unit}
        </span>
      </div>

      {trend && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.8rem",
            marginTop: "0.5rem",
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            color: trend.direction === "down" ? "var(--gruen)" : "var(--terracotta)",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            {trend.direction === "down" ? (
              <path d="M7 2v10M3 8l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            ) : (
              <path d="M7 12V2M3 6l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            )}
          </svg>
          {trend.percent}
        </div>
      )}

      {/* Tooltip */}
      {showTooltip && tooltipText && (
        <div
          style={{
            position: "absolute",
            top: -10,
            right: -10,
            zIndex: 100,
            background: "var(--kreide)",
            border: "1.5px solid var(--ink)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-floating)",
            padding: "1rem",
            width: 240,
            fontSize: "0.85rem",
            lineHeight: 1.5,
            animation: "bubbleIn 0.2s ease-out",
          }}
        >
          <button
            onClick={() => setShowTooltip(false)}
            style={{
              position: "absolute",
              top: "0.5rem",
              right: "0.75rem",
              background: "none",
              border: "none",
              fontSize: "1.1rem",
              cursor: "pointer",
              color: "var(--warm-grau)",
              lineHeight: 1,
            }}
          >
            ×
          </button>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.5rem",
              fontFamily: "var(--font-display)",
              fontWeight: 500,
              fontSize: "0.85rem",
            }}
          >
            {/* Mini avatar */}
            <svg width="28" height="28" viewBox="0 0 32 32">
              <rect x="4" y="4" width="24" height="24" rx="4" fill="none" stroke="#2C2C2C" strokeWidth="1.5" />
              <circle cx="12" cy="14" r="3.5" fill="none" stroke="#2C2C2C" strokeWidth="1.2" />
              <circle cx="20" cy="14" r="3.5" fill="none" stroke="#2C2C2C" strokeWidth="1.2" />
              <line x1="8.5" y1="14" x2="15.5" y2="14" stroke="#2C2C2C" strokeWidth="1.2" />
              <line x1="16.5" y1="14" x2="23.5" y2="14" stroke="#2C2C2C" strokeWidth="1.2" />
            </svg>
            Gridbert erklärt
          </div>
          {tooltipText}
        </div>
      )}
    </div>
  );
}
