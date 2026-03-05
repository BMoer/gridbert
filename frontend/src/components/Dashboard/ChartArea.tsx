import type { Widget } from "../../api/client";

interface Props {
  widget: Widget;
}

interface MonthlyDataPoint {
  month: string;
  value: number;
  previous?: number;
}

export function ChartArea({ widget }: Props) {
  const rawData = widget.config.monthly_data as MonthlyDataPoint[] | undefined;
  const title = (widget.config.title as string) || "Verbrauch letzte 12 Monate";

  // If widget has actual monthly data, render it dynamically
  if (rawData && rawData.length > 0) {
    return <DataChart title={title} data={rawData} />;
  }

  // Fallback: placeholder sketch chart
  return <PlaceholderChart title={title} />;
}

function DataChart({ title, data }: { title: string; data: MonthlyDataPoint[] }) {
  const maxVal = Math.max(...data.map((d) => Math.max(d.value, d.previous ?? 0)));
  const yMax = Math.ceil(maxVal / 100) * 100 || 400;
  const hasPrevious = data.some((d) => d.previous !== undefined);

  const chartLeft = 50;
  const chartRight = 430;
  const chartTop = 15;
  const chartBottom = 140;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;

  function toX(i: number): number {
    return chartLeft + (i / (data.length - 1)) * chartWidth;
  }
  function toY(val: number): number {
    return chartBottom - (val / yMax) * chartHeight;
  }

  function buildPath(values: number[]): string {
    return values
      .map((v, i) => `${i === 0 ? "M" : "L"}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
      .join(" ");
  }

  const currentPath = buildPath(data.map((d) => d.value));
  const previousPath = hasPrevious ? buildPath(data.map((d) => d.previous ?? 0)) : null;

  // Y-axis labels
  const ySteps = [0, Math.round(yMax / 2), yMax];

  return (
    <div className="card" style={{ gridArea: "chart", padding: "1.25rem", minHeight: 220, display: "flex", flexDirection: "column" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, marginBottom: "1rem", color: "var(--ink)" }}>
        {title}
      </div>
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        <svg viewBox="0 0 440 165" preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
          {/* Grid */}
          <line x1={chartLeft} y1={chartTop} x2={chartLeft} y2={chartBottom} stroke="#A89B8C" strokeWidth="0.5" strokeDasharray="2,4" />
          <line x1={chartLeft} y1={chartBottom} x2={chartRight} y2={chartBottom} stroke="#A89B8C" strokeWidth="0.5" />
          {ySteps.map((v) => (
            <g key={v}>
              {v > 0 && <line x1={chartLeft} y1={toY(v)} x2={chartRight} y2={toY(v)} stroke="#A89B8C" strokeWidth="0.3" strokeDasharray="4,6" />}
              <text x={chartLeft - 5} y={toY(v) + 4} fontFamily="var(--font-mono)" fontSize="10" fill="#A89B8C" textAnchor="end">{v}</text>
            </g>
          ))}
          {/* X-axis labels */}
          {data.map((d, i) => (
            i % Math.max(1, Math.floor(data.length / 6)) === 0 ? (
              <text key={i} x={toX(i)} y={chartBottom + 14} fontFamily="var(--font-mono)" fontSize="9" fill="#A89B8C" textAnchor="middle">
                {d.month}
              </text>
            ) : null
          ))}
          {/* Previous year line */}
          {previousPath && (
            <path d={previousPath} fill="none" stroke="#3B7DD8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.7">
              <animate attributeName="stroke-dasharray" from="0,2000" to="2000,0" dur="1.2s" fill="freeze" />
            </path>
          )}
          {/* Current line */}
          <path d={currentPath} fill="none" stroke="#C4654A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <animate attributeName="stroke-dasharray" from="0,2000" to="2000,0" dur="1.4s" fill="freeze" />
          </path>
          {/* Legend */}
          {hasPrevious && (
            <>
              <line x1="300" y1="8" x2="320" y2="8" stroke="#3B7DD8" strokeWidth="2" />
              <text x="324" y="11" fontFamily="var(--font-mono)" fontSize="9" fill="#A89B8C">Vorjahr</text>
            </>
          )}
          <line x1={hasPrevious ? 370 : 300} y1="8" x2={hasPrevious ? 390 : 320} y2="8" stroke="#C4654A" strokeWidth="2" />
          <text x={hasPrevious ? 394 : 324} y="11" fontFamily="var(--font-mono)" fontSize="9" fill="#A89B8C">Aktuell</text>
        </svg>
      </div>
    </div>
  );
}

function PlaceholderChart({ title }: { title: string }) {
  return (
    <div className="card" style={{ gridArea: "chart", padding: "1.25rem", minHeight: 220, display: "flex", flexDirection: "column" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, marginBottom: "1rem", color: "var(--ink)" }}>
        {title}
      </div>
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        <svg viewBox="0 0 440 160" preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
          <line x1="40" y1="10" x2="40" y2="140" stroke="#A89B8C" strokeWidth="0.5" strokeDasharray="2,4" />
          <line x1="40" y1="140" x2="430" y2="140" stroke="#A89B8C" strokeWidth="0.5" />
          <line x1="40" y1="75" x2="430" y2="75" stroke="#A89B8C" strokeWidth="0.3" strokeDasharray="4,6" />
          <text x="35" y="14" fontFamily="var(--font-mono)" fontSize="10" fill="#A89B8C" textAnchor="end">400</text>
          <text x="35" y="78" fontFamily="var(--font-mono)" fontSize="10" fill="#A89B8C" textAnchor="end">200</text>
          <text x="35" y="144" fontFamily="var(--font-mono)" fontSize="10" fill="#A89B8C" textAnchor="end">0</text>
          <polygon points="430,136 438,140 430,144" fill="#2C2C2C" />
          <path d="M55,95 C70,90 80,70 105,65 S140,55 170,50 S200,40 235,30 S270,35 300,55 S330,70 360,80 S390,85 415,75" fill="none" stroke="#3B7DD8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <animate attributeName="stroke-dasharray" from="0,1000" to="500,0" dur="1.2s" fill="freeze" />
          </path>
          <path d="M55,110 C70,105 80,95 105,85 S140,70 170,65 S200,60 235,55 S270,60 300,70 S330,85 360,95 S390,100 415,90" fill="none" stroke="#C4654A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <animate attributeName="stroke-dasharray" from="0,1000" to="500,0" dur="1.4s" fill="freeze" />
          </path>
        </svg>
      </div>
    </div>
  );
}
