import { useDashboardStore } from "../../stores/dashboardStore";
import { useChat } from "../../hooks/useChat";

interface TaskItem {
  label: string;
  done: boolean;
  /** Message sent to Gridbert when clicked (if not done). */
  chatPrompt: string;
}

interface Props {
  onOpenChat: () => void;
}

export function TaskList({ onOpenChat }: Props) {
  const widgets = useDashboardStore((s) => s.widgets);
  const userFiles = useDashboardStore((s) => s.userFiles);
  const { sendMessage, isLoading } = useChat();

  // Derive tasks from user state — focused 3-step journey
  const tasks: TaskItem[] = [
    {
      label: "Stromrechnung hochgeladen",
      done: userFiles.some((f) => f.media_type === "application/pdf" || f.file_name.endsWith(".pdf")),
      chatPrompt: "Ich möchte meine Stromrechnung hochladen. Wie mache ich das?",
    },
    {
      label: "Tarife verglichen",
      done: widgets.some((w) => w.widget_type === "tariff_comparison"),
      chatPrompt: "Vergleiche bitte die Stromtarife für mich.",
    },
    {
      label: "Tarifwechsel eingeleitet",
      done: widgets.some((w) => w.widget_type === "switching_status"),
      chatPrompt: "Ich möchte den Tarif wechseln.",
    },
  ];

  function handleClick(task: TaskItem) {
    if (task.done || isLoading) return;
    onOpenChat();
    // Small delay so drawer opens before message is sent
    setTimeout(() => sendMessage(task.chatPrompt), 300);
  }

  return (
    <div className="card" style={{ gridArea: "tasks" }}>
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1rem",
          fontWeight: 500,
          marginBottom: "0.85rem",
          color: "var(--ink)",
        }}
      >
        Deine Schritte
      </div>

      {tasks.map((task) => (
        <button
          key={task.label}
          type="button"
          onClick={() => handleClick(task)}
          disabled={isLoading}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "0.6rem",
            marginBottom: "0.65rem",
            fontSize: "0.9rem",
            lineHeight: 1.4,
            color: task.done ? "var(--warm-grau)" : "var(--ink)",
            textDecoration: task.done ? "line-through" : "none",
            textDecorationColor: task.done ? "var(--warm-grau)" : undefined,
            background: "none",
            border: "none",
            padding: 0,
            cursor: task.done ? "default" : "pointer",
            textAlign: "left",
            width: "100%",
            fontFamily: "inherit",
            transition: "opacity 0.15s",
            opacity: isLoading ? 0.6 : 1,
          }}
          onMouseEnter={(e) => {
            if (!task.done) e.currentTarget.style.color = "var(--terracotta)";
          }}
          onMouseLeave={(e) => {
            if (!task.done) e.currentTarget.style.color = "var(--ink)";
          }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="10" cy="10" r="8" fill="none" stroke={task.done ? "#4A8B6E" : "#A89B8C"} strokeWidth="1.5" />
            {task.done && (
              <path d="M6,10 L9,13 L14,7" stroke="#4A8B6E" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            )}
          </svg>
          {task.label}
        </button>
      ))}
    </div>
  );
}
