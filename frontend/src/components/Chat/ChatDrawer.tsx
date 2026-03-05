import { useEffect, useRef } from "react";
import { useChatStore } from "../../stores/chatStore";
import { useChat } from "../../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ChatDrawer({ open, onClose }: Props) {
  const messages = useChatStore((s) => s.messages);
  const { sendMessage, isLoading } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          onClick={onClose}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(44,44,44,0.2)",
            zIndex: 90,
            transition: "opacity 0.2s",
          }}
        />
      )}

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          width: "min(420px, 100vw)",
          height: "100vh",
          background: "var(--bone)",
          boxShadow: open ? "var(--shadow-floating)" : "none",
          transform: open ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.3s ease",
          zIndex: 100,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          className="sketch-border-bottom"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "1rem 1.25rem",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "var(--ink)",
            }}
          >
            Grid<span style={{ color: "var(--terracotta)" }}>bert</span>
          </span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: "1.5rem",
              cursor: "pointer",
              color: "var(--warm-grau)",
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "1rem",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                textAlign: "center",
                color: "var(--warm-grau)",
                fontFamily: "var(--font-body)",
                gap: "0.5rem",
              }}
            >
              <span style={{ fontSize: "2rem" }}>?</span>
              <p>Frag mich was über deine Energie.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onSuggestionClick={!isLoading ? sendMessage : undefined}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput onSend={(msg, files) => sendMessage(msg, files)} disabled={isLoading} />
      </div>
    </>
  );
}
