import { type FormEvent, useState } from "react";
import { useChat } from "../../hooks/useChat";

interface Props {
  onOpenChat: () => void;
}

export function QuestionArea({ onOpenChat }: Props) {
  const [text, setText] = useState("");
  const { sendMessage, isLoading } = useChat();

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    const msg = text.trim();
    setText("");
    onOpenChat();
    // Small delay so drawer opens before message sends
    setTimeout(() => sendMessage(msg), 300);
  }

  return (
    <div
      style={{
        gridArea: "question",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 140,
        border: "2px dashed var(--warm-grau)",
        background: "transparent",
        borderRadius: "var(--radius-md)",
        padding: "1.25rem",
        animation: "fadeInUp 0.5s ease-out 0.33s backwards",
        gap: "0.75rem",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "2rem",
          fontWeight: 700,
          color: "var(--terracotta)",
          lineHeight: 1,
          opacity: 0.7,
        }}
      >
        ?
      </div>

      <form onSubmit={handleSubmit} style={{ width: "100%", display: "flex", gap: "0.5rem" }}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Frag mich was..."
          disabled={isLoading}
          style={{
            flex: 1,
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            padding: "0.5rem 0.75rem",
            border: "1.5px solid var(--warm-grau)",
            borderRadius: "var(--radius-md)",
            background: "var(--kreide)",
            color: "var(--ink)",
            outline: "none",
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; }}
        />
        <button
          type="submit"
          disabled={isLoading || !text.trim()}
          style={{
            background: "var(--terracotta)",
            color: "white",
            border: "none",
            borderRadius: "var(--radius-md)",
            padding: "0.5rem 0.75rem",
            cursor: "pointer",
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            opacity: isLoading || !text.trim() ? 0.5 : 1,
          }}
        >
          &rarr;
        </button>
      </form>
    </div>
  );
}
