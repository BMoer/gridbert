import { useEffect, useState } from "react";
import { getConversations, getMessages, type Conversation } from "../../api/client";
import { useChatStore, type ChatMessage } from "../../stores/chatStore";
import { useAuthStore } from "../../stores/authStore";

interface Props {
  onOpenChat?: () => void;
}

export function Header({ onOpenChat }: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const currentConvId = useChatStore((s) => s.conversationId);
  const reset = useChatStore((s) => s.reset);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    getConversations()
      .then(setConversations)
      .catch(() => {});
  }, [currentConvId]);

  async function loadConversation(conv: Conversation) {
    if (conv.id === currentConvId) return;
    setMenuOpen(false);
    try {
      const msgs = await getMessages(conv.id);
      const chatMessages: ChatMessage[] = msgs.map((m, i) => ({
        id: `db-${m.id ?? i}`,
        role: m.role as "user" | "assistant",
        content: m.content,
      }));
      const store = useChatStore.getState();
      store.setConversationId(conv.id);
      store.loadMessages(chatMessages);
    } catch {
      // ignore
    }
  }

  return (
    <header
      className="sketch-border-bottom"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "1rem",
        marginBottom: "2.5rem",
        paddingBottom: "1.5rem",
      }}
    >
      {/* Logo */}
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.75rem",
          fontWeight: 700,
          letterSpacing: "-0.02em",
          color: "var(--ink)",
        }}
      >
        Grid<span style={{ color: "var(--terracotta)" }}>bert</span>
      </div>

      {/* Chat button */}
      {onOpenChat && (
        <button
          onClick={onOpenChat}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "0.85rem",
            color: "var(--terracotta)",
            background: "none",
            border: "1.5px solid var(--terracotta)",
            borderRadius: "var(--radius-md)",
            padding: "0.35rem 0.75rem",
            cursor: "pointer",
          }}
        >
          Chat
        </button>
      )}

      <div style={{ flex: 1 }} />

      {/* Conversation selector */}
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "0.875rem",
            color: "var(--warm-grau)",
            background: "none",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
          }}
        >
          {conversations.find((c) => c.id === currentConvId)?.title || "Neues Gespräch"}
          <span style={{ fontSize: "0.7rem" }}>▾</span>
        </button>

        {menuOpen && (
          <div
            style={{
              position: "absolute",
              top: "100%",
              right: 0,
              marginTop: "0.5rem",
              background: "var(--kreide)",
              border: "1.5px solid var(--ink)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-floating)",
              minWidth: "240px",
              zIndex: 50,
              overflow: "hidden",
            }}
          >
            <button
              onClick={() => {
                reset();
                setMenuOpen(false);
              }}
              style={{
                width: "100%",
                padding: "0.6rem 1rem",
                fontFamily: "var(--font-body)",
                fontSize: "0.875rem",
                fontWeight: 600,
                color: "var(--terracotta)",
                background: "none",
                border: "none",
                borderBottom: "1px solid var(--warm-grau)",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              + Neues Gespräch
            </button>
            <div style={{ maxHeight: "240px", overflowY: "auto" }}>
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv)}
                  style={{
                    width: "100%",
                    padding: "0.5rem 1rem",
                    fontFamily: "var(--font-body)",
                    fontSize: "0.85rem",
                    color: conv.id === currentConvId ? "var(--terracotta)" : "var(--ink)",
                    background: conv.id === currentConvId ? "rgba(196,101,74,0.06)" : "none",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {conv.title || "Neuer Chat"}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* User */}
      <span
        style={{
          fontFamily: "var(--font-body)",
          fontSize: "0.85rem",
          color: "var(--warm-grau)",
        }}
      >
        {user?.name || user?.email}
      </span>
      <button
        onClick={logout}
        style={{
          fontFamily: "var(--font-body)",
          fontSize: "0.75rem",
          color: "var(--warm-grau)",
          background: "none",
          border: "none",
          cursor: "pointer",
        }}
      >
        Abmelden
      </button>
    </header>
  );
}
