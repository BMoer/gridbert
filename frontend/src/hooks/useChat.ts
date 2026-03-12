import { useCallback, useRef } from "react";
import { useChatStore } from "../stores/chatStore";
import { useDashboardStore } from "../stores/dashboardStore";
import { BASE } from "../api/client";

export interface FileAttachment {
  name: string;
  type: string;
  data: string; // base64
}

/** Hook that sends a message and streams the SSE response. */
export function useChat() {
  const isLoading = useChatStore((s) => s.isLoading);
  const abortRef = useRef<AbortController | null>(null);

  const cancelRequest = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  const sendMessage = useCallback(
    async (message: string, files?: FileAttachment[]) => {
      const state = useChatStore.getState();
      if (!message.trim() || state.isLoading) return;

      state.addUserMessage(message);
      state.setLoading(true);
      state.startAssistantMessage();

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const token = localStorage.getItem("gridbert_token");

        const attachments = files?.map((f) => ({
          type: f.type.startsWith("image/") ? "image" : "document",
          media_type: f.type,
          file_name: f.name,
          data: f.data,
        }));

        const res = await fetch(`${BASE}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message,
            conversation_id: state.conversationId,
            attachments: attachments?.length ? attachments : undefined,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          if (res.status === 401) {
            localStorage.removeItem("gridbert_token");
            window.location.href = "/login";
            return;
          }
          const err = await res.json().catch(() => ({ detail: "Fehler" }));
          if (res.status === 503 && err.detail === "NO_API_KEY") {
            state.appendToAssistant(
              "Ich brauche einen API-Schlüssel, um dir helfen zu können. " +
              "Bitte richte ihn unter [Einstellungen](/settings) ein.",
            );
          } else {
            state.appendToAssistant(`Fehler: ${err.detail}`);
          }
          state.finishAssistantMessage();
          state.setLoading(false);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const dataLine = line.replace(/^data: /, "").trim();
            if (!dataLine) continue;

            try {
              const event = JSON.parse(dataLine);
              handleEvent(event);
            } catch {
              // ignore parse errors
            }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          useChatStore.getState().appendToAssistant("Abgebrochen.");
        } else {
          useChatStore.getState().appendToAssistant("Verbindungsfehler. Bitte erneut versuchen.");
        }
      } finally {
        abortRef.current = null;
        const s = useChatStore.getState();
        s.finishAssistantMessage();
        s.setLoading(false);
      }
    },
    [],
  );

  return { sendMessage, isLoading, cancelRequest };
}

function handleEvent(event: { type: string; data: Record<string, unknown> }) {
  const store = useChatStore.getState();
  const dashStore = useDashboardStore.getState();

  switch (event.type) {
    case "text_delta":
      store.appendToAssistant(event.data.text as string);
      break;
    case "tool_start":
      store.addToolActivity(
        event.data.tool as string,
        event.data.input as Record<string, unknown> | undefined,
      );
      break;
    case "tool_result":
      store.completeToolActivity(
        event.data.tool as string,
        event.data.summary as string,
      );
      break;
    case "status":
      store.setStatusMessage(event.data.message as string);
      break;
    case "widget_add": {
      const widget = event.data as unknown as import("../api/client").Widget;
      dashStore.addWidget(widget);
      break;
    }
    case "widget_update": {
      const widget = event.data as unknown as import("../api/client").Widget;
      dashStore.updateWidget(widget);
      break;
    }
    case "error":
      store.appendToAssistant(
        `Fehler: ${(event.data.message as string) || "Unbekannter Fehler"}`,
      );
      break;
    case "done":
      if (event.data.conversation_id) {
        store.setConversationId(event.data.conversation_id as number);
      }
      if (event.data.suggestions) {
        store.setSuggestions(event.data.suggestions as string[]);
      }
      dashStore.refreshContext();
      break;
  }
}
