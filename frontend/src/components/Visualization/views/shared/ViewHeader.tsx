interface Props {
  title: string;
  subtitle?: string;
}

/** Consistent header for all dedicated views. */
export function ViewHeader({ title, subtitle }: Props) {
  return (
    <div style={{ marginBottom: "0.5rem" }}>
      <h2
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.35rem",
          fontWeight: 600,
          color: "var(--ink)",
          margin: 0,
        }}
      >
        {title}
      </h2>
      {subtitle && (
        <p
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            color: "var(--warm-grau)",
            margin: "0.25rem 0 0",
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
