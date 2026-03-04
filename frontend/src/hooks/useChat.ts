import { useCallback } from "react";
import { useChatStore } from "../stores/chatStore";

export interface FileAttachment {
  name: string;
  type: string;
  data: string; // base64
}

/** Hook that sends a message and streams the SSE response. */
export function useChat() {
  const isLoading = useChatStore((s) => s.isLoading);

  const sendMessage = useCallback(
    async (message: string, files?: FileAttachment[]) => {
      // Read fresh state to avoid stale closures
      const state = useChatStore.getState();
      if (!message.trim() || state.isLoading) return;

      // Debug: log what we received
      console.log("[useChat] sendMessage", {
        message,
        filesReceived: files?.length ?? 0,
        fileDetails: files?.map((f) => ({ name: f.name, type: f.type, dataLen: f.data?.length ?? 0 })),
      });

      state.addUserMessage(message);
      state.setLoading(true);
      state.startAssistantMessage();

      try {
        const token = localStorage.getItem("gridbert_token");

        // Build attachments from files
        const attachments = files?.map((f) => ({
          type: f.type.startsWith("image/") ? "image" : "document",
          media_type: f.type,
          file_name: f.name,
          data: f.data,
        }));

        console.log("[useChat] sending to /api/chat", {
          attachmentsCount: attachments?.length ?? 0,
          bodySize: JSON.stringify({ message, conversation_id: state.conversationId, attachments: attachments?.length ? attachments : undefined }).length,
        });

        const res = await fetch("/api/chat", {
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
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Fehler" }));
          state.appendToAssistant(`Fehler: ${err.detail}`);
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
      } catch {
        useChatStore.getState().appendToAssistant("Verbindungsfehler. Bitte erneut versuchen.");
      } finally {
        const s = useChatStore.getState();
        s.finishAssistantMessage();
        s.setLoading(false);
      }
    },
    [], // no deps — we use getState() for fresh values
  );

  return { sendMessage, isLoading };
}

function handleEvent(event: { type: string; data: Record<string, unknown> }) {
  const store = useChatStore.getState();
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
    case "done":
      if (event.data.conversation_id) {
        store.setConversationId(event.data.conversation_id as number);
      }
      break;
  }
}
