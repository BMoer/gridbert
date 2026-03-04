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
          <WelcomeScreen onSuggestion={sendMessage} />
        ) : (
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
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

function WelcomeScreen({ onSuggestion }: { onSuggestion: (msg: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gridbert-100">
        <span className="text-3xl">&#9889;</span>
      </div>
      <h2 className="text-xl font-semibold text-gray-800">Hallo! Ich bin Gridbert.</h2>
      <p className="mt-2 max-w-md text-gray-500">
        Dein persönlicher Energie-Agent. Erzähl mir von deiner Energiesituation
        oder lad deine Stromrechnung hoch — ich finde Sparpotenziale für dich.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {[
          "Was kannst du für mich tun?",
          "Vergleiche Stromtarife für 1060 Wien",
          "Ich verbrauche 3200 kWh im Jahr",
        ].map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestion(suggestion)}
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-sm text-gray-600 hover:border-gridbert-300 hover:bg-gridbert-50"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
