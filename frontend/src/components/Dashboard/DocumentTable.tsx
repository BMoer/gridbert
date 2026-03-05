import { useRef, useState } from "react";
import { useDashboardStore } from "../../stores/dashboardStore";
import { useChat, type FileAttachment } from "../../hooks/useChat";

export function DocumentTable() {
  const userFiles = useDashboardStore((s) => s.userFiles);
  const userMemory = useDashboardStore((s) => s.userMemory);
  const { sendMessage } = useChat();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(fileList: FileList) {
    const files = Array.from(fileList);
    const attachments: FileAttachment[] = [];
    let pending = files.length;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1] ?? "";
        if (base64) {
          attachments.push({ name: file.name, type: file.type, data: base64 });
        }
        pending--;
        if (pending === 0 && attachments.length > 0) {
          const msg = `Analysiere ${attachments.map((a) => a.name).join(", ")}`;
          sendMessage(msg, attachments);
        }
      };
      reader.readAsDataURL(file);
    });
  }

  const hasContent = userFiles.length > 0 || userMemory.length > 0;

  return (
    <div
      className="card"
      style={{
        gridArea: "table",
        padding: "1.5rem",
        border: "1.5px solid var(--ink)",
        borderRadius: "var(--radius-lg)",
        display: "flex",
        alignItems: hasContent ? "flex-start" : "center",
        flexWrap: "wrap",
        gap: hasContent ? "1.5rem" : "2rem",
        minHeight: 160,
        background: "var(--kreide)",
        animation: dragOver ? "uploadPulse 1s ease-in-out infinite" : undefined,
        borderColor: dragOver ? "var(--terracotta)" : undefined,
        cursor: "pointer",
      }}
      onClick={() => fileInputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) handleFiles(e.target.files);
          e.target.value = "";
        }}
        accept=".pdf,.csv,.xlsx,.xls,image/*,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        multiple
        style={{ display: "none" }}
      />

      {hasContent ? (
        <>
          {/* Stored files */}
          {userFiles.length > 0 && (
            <div style={{ flex: "1 1 200px", minWidth: 200 }}>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  marginBottom: "0.5rem",
                  color: "var(--ink)",
                }}
              >
                Deine Unterlagen
              </div>
              {userFiles.map((f) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "0.35rem",
                    fontSize: "0.85rem",
                    color: "var(--ink)",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.65rem",
                      color: "var(--terracotta)",
                      fontWeight: 600,
                    }}
                  >
                    {f.file_name.split(".").pop()?.toUpperCase()}
                  </span>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {f.file_name}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--warm-grau)", flexShrink: 0 }}>
                    {f.size_bytes > 1024 ? `${Math.round(f.size_bytes / 1024)}KB` : `${f.size_bytes}B`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* User knowledge */}
          {userMemory.length > 0 && (
            <div style={{ flex: "1 1 200px", minWidth: 200 }}>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  marginBottom: "0.5rem",
                  color: "var(--ink)",
                }}
              >
                Was ich über dich weiß
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                {userMemory.map((m) => (
                  <span
                    key={m.id}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.75rem",
                      background: "var(--bone)",
                      padding: "0.2rem 0.5rem",
                      borderRadius: "var(--radius-sm)",
                      color: "var(--ink)",
                    }}
                  >
                    {m.fact_key}: {m.fact_value}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Upload CTA */}
          <div
            style={{
              flex: "0 0 auto",
              textAlign: "center",
              color: "var(--warm-grau)",
              fontFamily: "var(--font-body)",
              fontSize: "0.8rem",
            }}
          >
            + Weitere Unterlage
          </div>
        </>
      ) : (
        <>
          {/* Empty state: sketch doc icons + invitation */}
          <svg width="72" height="88" viewBox="0 0 72 88" fill="none" style={{ flexShrink: 0 }}>
            <rect x="4" y="4" width="54" height="70" rx="3" stroke="#2C2C2C" strokeWidth="1.5" fill="var(--kreide)" transform="rotate(-5 31 39)" />
            <text x="22" y="48" fontFamily="JetBrains Mono, monospace" fontSize="11" fill="#2C2C2C" fontWeight="600" transform="rotate(-5 31 39)">e.pdf</text>
            <path d="M15,28 L45,28" stroke="#A89B8C" strokeWidth="1" strokeDasharray="2,2" transform="rotate(-5 31 39)" />
            <path d="M15,35 L40,35" stroke="#A89B8C" strokeWidth="1" strokeDasharray="2,2" transform="rotate(-5 31 39)" />
          </svg>

          <div
            style={{
              flex: 1,
              fontFamily: "var(--font-display)",
              fontSize: "1.35rem",
              fontWeight: 400,
              fontStyle: "italic",
              color: "var(--ink)",
              lineHeight: 1.4,
              opacity: 0.75,
            }}
          >
            Hallo, ich bin <strong style={{ fontStyle: "normal", fontWeight: 600, color: "var(--terracotta)" }}>Gridbert</strong>.
            Leg deine Unterlagen auf den Tisch — ich schau mir das an.
          </div>

          <svg width="72" height="88" viewBox="0 0 72 88" fill="none" style={{ flexShrink: 0 }}>
            <rect x="10" y="8" width="54" height="70" rx="3" stroke="#2C2C2C" strokeWidth="1.5" fill="var(--kreide)" transform="rotate(4 37 43)" />
            <text x="14" y="38" fontFamily="JetBrains Mono, monospace" fontSize="8" fill="#2C2C2C" fontWeight="600" transform="rotate(4 37 43)">Lastgang</text>
            <text x="22" y="52" fontFamily="JetBrains Mono, monospace" fontSize="10" fill="#C4654A" fontWeight="600" transform="rotate(4 37 43)">.csv</text>
            <path d="M18,60 L52,60" stroke="#A89B8C" strokeWidth="1" strokeDasharray="2,2" transform="rotate(4 37 43)" />
          </svg>
        </>
      )}
    </div>
  );
}
