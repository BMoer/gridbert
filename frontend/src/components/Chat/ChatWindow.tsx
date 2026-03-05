import { useEffect, useRef } from "react";
import { useChatStore } from "../../stores/chatStore";
import { useChat } from "../../hooks/useChat";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";

export function ChatWindow() {
  const messages = useChatStore((s) => s.messages);
  const { sendMessage, isLoading } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
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
          <div className="mx-auto max-w-2xl space-y-4">
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
      <div className="mx-auto w-full max-w-2xl">
        <ChatInput onSend={(msg, files) => sendMessage(msg, files)} disabled={isLoading} />
      </div>
    </div>
  );
}
