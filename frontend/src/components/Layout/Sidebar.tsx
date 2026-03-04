import { useEffect, useState } from "react";
import { getConversations, getMessages, type Conversation } from "../../api/client";
import { useChatStore, type ChatMessage } from "../../stores/chatStore";
import { useAuthStore } from "../../stores/authStore";

export function Sidebar() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
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
      // ignore load errors
    }
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r border-gray-200 bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-4">
        <span className="text-xl">&#9889;</span>
        <span className="text-lg font-bold text-gridbert-600">Gridbert</span>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <button
          onClick={() => reset()}
          className="flex w-full items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
        >
          <span>+</span> Neuer Chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-3">
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => loadConversation(conv)}
            className={`mb-1 w-full truncate rounded-lg px-3 py-2 text-left text-sm ${
              conv.id === currentConvId
                ? "bg-gridbert-100 text-gridbert-700"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            {conv.title || "Neuer Chat"}
          </button>
        ))}
      </div>

      {/* User footer */}
      <div className="border-t border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="truncate text-sm text-gray-600">{user?.name || user?.email}</span>
          <button
            onClick={logout}
            className="text-xs text-gray-400 hover:text-red-500"
          >
            Abmelden
          </button>
        </div>
      </div>
    </aside>
  );
}
