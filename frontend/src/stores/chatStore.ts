import { create } from "zustand";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
  toolActivity?: ToolActivity[];
}

export interface ToolActivity {
  tool: string;
  status: "running" | "done";
  input?: Record<string, unknown>;
  summary?: string;
}

interface ChatState {
  messages: ChatMessage[];
  conversationId: number | null;
  isLoading: boolean;
  addUserMessage: (content: string) => void;
  startAssistantMessage: () => void;
  appendToAssistant: (text: string) => void;
  addToolActivity: (tool: string, input?: Record<string, unknown>) => void;
  completeToolActivity: (tool: string, summary: string) => void;
  finishAssistantMessage: () => void;
  setConversationId: (id: number) => void;
  setLoading: (loading: boolean) => void;
  loadMessages: (msgs: ChatMessage[]) => void;
  reset: () => void;
}

let msgCounter = 0;

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  conversationId: null,
  isLoading: false,

  addUserMessage: (content) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: `msg-${++msgCounter}`, role: "user", content },
      ],
    })),

  startAssistantMessage: () =>
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: `msg-${++msgCounter}`,
          role: "assistant",
          content: "",
          isStreaming: true,
          toolActivity: [],
        },
      ],
    })),

  appendToAssistant: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + text };
      }
      return { messages: msgs };
    }),

  addToolActivity: (tool, input) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const activity = [...(last.toolActivity ?? []), { tool, status: "running" as const, input }];
        msgs[msgs.length - 1] = { ...last, toolActivity: activity };
      }
      return { messages: msgs };
    }),

  completeToolActivity: (tool, summary) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        const activity = (last.toolActivity ?? []).map((a) =>
          a.tool === tool && a.status === "running"
            ? { ...a, status: "done" as const, summary }
            : a,
        );
        msgs[msgs.length - 1] = { ...last, toolActivity: activity };
      }
      return { messages: msgs };
    }),

  finishAssistantMessage: () =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { messages: msgs };
    }),

  setConversationId: (id) => set({ conversationId: id }),
  setLoading: (loading) => set({ isLoading: loading }),
  loadMessages: (msgs) => set({ messages: msgs }),
  reset: () => set({ messages: [], conversationId: null, isLoading: false }),
}));
