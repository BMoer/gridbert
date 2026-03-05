import type { Widget } from "../../api/client";

interface Props {
  widget: Widget;
}

interface MonthlyDataPoint {
  month: string;
  value: number;
  previous?: number;
}

/** Short German month labels. */
const MONTH_LABELS: Record<string, string> = {
  "01": "Jan", "02": "Feb", "03": "Mär", "04": "Apr",
  "05": "Mai", "06": "Jun", "07": "Jul", "08": "Aug",
  "09": "Sep", "10": "Okt", "11": "Nov", "12": "Dez",
};

function monthLabel(key: string): string {
  const mm = key.split("-")[1];
  return mm ? (MONTH_LABELS[mm] ?? key) : key;
}

export function ChartArea({ widget }: Props) {
  const rawData = widget.config.monthly_data as MonthlyDataPoint[] | undefined;
  const title = (widget.config.title as string) || "Verbrauch letzte 12 Monate";
  const monthlyImg = widget.config.monthly_chart_base64 as string | undefined;

  // Priority 1: matplotlib PNG
  if (monthlyImg) {
    const src = monthlyImg.startsWith("data:") ? monthlyImg : `data:image/png;base64,${monthlyImg}`;
    return (
      <div className="card" style={{ padding: "1.25rem", minHeight: 220, display: "flex", flexDirection: "column" }}>
        <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, marginBottom: "1rem", color: "var(--ink)" }}>
          {title}
        </div>
        <img src={src} alt={title} style={{ width: "100%", borderRadius: "var(--radius-sm)" }} />
      </div>
    );
  }

  // Priority 2: SVG bar chart from data
  if (rawData && rawData.length > 0) {
    return <BarChart title={title} data={rawData} />;
  }

  // Fallback: placeholder
  return <PlaceholderChart title={title} />;
}

function BarChart({ title, data }: { title: string; data: MonthlyDataPoint[] }) {
  const maxVal = Math.max(...data.map((d) => d.value));
  const yMax = Math.ceil(maxVal / 100) * 100 || 400;

  const chartLeft = 55;
  const chartRight = 430;
  const chartTop = 15;
  const chartBottom = 145;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;
  const barGap = 4;
  const barWidth = (chartWidth - barGap * data.length) / data.length;

  function toY(val: number): number {
    return chartBottom - (val / yMax) * chartHeight;
  }

  // Y-axis labels
  const ySteps = [0, Math.round(yMax / 2), yMax];

  return (
    <div className="card" style={{ padding: "1.25rem", minHeight: 220, display: "flex", flexDirection: "column" }}>
      <div style={{ fontFamily: "var(--font-display)", fontSize: "1rem", fontWeight: 500, marginBottom: "1rem", color: "var(--ink)" }}>
        {title}
      </div>
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        <svg viewBox="0 0 440 170" preserveAspectRatio="xMidYMid meet" style={{ width: "100%", height: "100%" }}>
          {/* Grid */}
          <line x1={chartLeft} y1={chartTop} x2={chartLeft} y2={chartBottom} stroke="#A89B8C" strokeWidth="0.5" />
          <line x1={chartLeft} y1={chartBottom} x2={chartRight} y2={chartBottom} stroke="#A89B8C" strokeWidth="0.5" />
          {ySteps.map((v) => (
            <g key={v}>
              {v > 0 && <line x1={chartLeft} y1={toY(v)} x2={chartRight} y2={toY(v)} stroke="#A89B8C" strokeWidth="0.3" strokeDasharray="4,6" />}
              <text x={chartLeft - 5} y={toY(v) + 4} fontFamily="var(--font-mono)" fontSize="9" fill="#A89B8C" textAnchor="end">{v}</text>
            </g>
          ))}

          {/* Bars */}
          {data.map((d, i) => {
            const x = chartLeft + barGap / 2 + i * (barWidth + barGap);
            const h = (d.value / yMax) * chartHeight;
            const y = chartBottom - h;
            return (
              <g key={i}>
                <rect x={x} y={y} width={barWidth} height={h} fill="#C4654A" rx="2" opacity="0.85">
                  <animate attributeName="height" from="0" to={h} dur="0.6s" fill="freeze" />
                  <animate attributeName="y" from={chartBottom} to={y} dur="0.6s" fill="freeze" />
                </rect>
                {/* Value label on top */}
                {barWidth > 20 && (
                  <text
                    x={x + barWidth / 2}
                    y={y - 3}
                    fontFamily="var(--font-mono)"
                    fontSize="7"
                    fill="var(--ink)"
                    textAnchor="middle"
                    opacity="0.7"
                  >
                    {Math.round(d.value)}
                  </text>
                )}
                {/* Month label */}
                <text
                  x={x + barWidth / 2}
                  y={chartBottom + 12}
                  fontFamily="var(--font-mono)"
                  fontSize="8"
                  fill="#A89B8C"
                  textAnchor="middle"
                >
                  {monthLabel(d.month)}
                </text>
              </g>
            );
          })}

          {/* Y-axis unit */}
          <text x={chartLeft - 5} y={8} fontFamily="var(--font-mono)" fontSize="8" fill="#A89B8C" textAnchor="end">kWh</text>
        </svg>
      </div>
    </div>
  );
}

function PlaceholderChart({ title }: { title: string }) {
  return (
    <div className="card" style={{ padding: "1.25rem", minHeight: 220, display: "flex", flexDirection: "column" }}>
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
