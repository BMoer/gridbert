import { useEffect, useState } from "react";
import { getEnergyNews, type NewsItem } from "../../api/client";

export function NewsArea() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEnergyNews()
      .then((items) => setNews(items.slice(0, 5)))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function tagInfo(kategorie: string): { label: string; color: string } {
    if (kategorie === "markt") return { label: "Markt", color: "var(--info)" };
    return { label: "Betrifft dich", color: "var(--terracotta)" };
  }

  return (
    <div className="card" style={{ gridArea: "news", overflow: "hidden" }}>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1rem",
          fontWeight: 500,
          marginBottom: "0.85rem",
          color: "var(--ink)",
        }}
      >
        Neuigkeiten
      </div>

      {loading && (
        <div style={{ fontSize: "0.85rem", color: "var(--warm-grau)" }}>Lade News...</div>
      )}

      {!loading && news.length === 0 && (
        <div style={{ fontSize: "0.85rem", color: "var(--warm-grau)", fontStyle: "italic" }}>
          Keine Energie-News verfügbar.
        </div>
      )}

      {news.map((item, i) => {
        const tag = tagInfo(item.kategorie);
        return (
          <a
            key={i}
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: "none", color: "inherit", display: "block" }}
          >
            <div
              className="sketch-border-left"
              style={{ paddingLeft: "0.85rem", marginBottom: "0.75rem" }}
            >
              <h4
                style={{
                  fontFamily: "var(--font-body)",
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  lineHeight: 1.3,
                  marginBottom: "0.2rem",
                  color: "var(--ink)",
                }}
              >
                {item.titel}
              </h4>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.6rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: "var(--kreide)",
                    background: tag.color,
                    padding: "0.1rem 0.35rem",
                    borderRadius: "var(--radius-sm)",
                    display: "inline-block",
                  }}
                >
                  {tag.label}
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--warm-grau)" }}>
                  {item.quelle}
                </span>
              </div>
            </div>
          </a>
        );
      })}
    </div>
  );
}
