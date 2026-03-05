import { type FormEvent, useState, useRef, useEffect } from "react";
import type { FileAttachment } from "../../hooks/useChat";

interface Props {
  onSend: (message: string, files?: FileAttachment[]) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<FileAttachment[]>([]);
  const [pendingReads, setPendingReads] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filesReady = pendingReads === 0;

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [text]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if ((!text.trim() && files.length === 0) || disabled || !filesReady) return;
    const msg = text.trim() || (files.length > 0 ? `Analysiere ${files.map((f) => f.name).join(", ")}` : "");
    onSend(msg, files.length > 0 ? files : undefined);
    setText("");
    setFiles([]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files;
    if (!selected) return;

    const fileArray = Array.from(selected);
    setPendingReads((prev) => prev + fileArray.length);

    fileArray.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1] ?? "";
        if (base64) {
          setFiles((prev) => [...prev, { name: file.name, type: file.type, data: base64 }]);
        }
        setPendingReads((prev) => prev - 1);
      };
      reader.onerror = () => {
        console.error(`[ChatInput] FileReader error for: ${file.name}`);
        setPendingReads((prev) => prev - 1);
      };
      reader.readAsDataURL(file);
    });

    // Reset input so same file can be selected again
    e.target.value = "";
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  return (
    <form onSubmit={handleSubmit} className="p-4" style={{ borderTop: "1px solid var(--warm-grau)", background: "var(--kreide)" }}>
      {/* File preview */}
      {(files.length > 0 || pendingReads > 0) && (
        <div className="mb-2 flex flex-wrap gap-2">
          {files.map((file, i) => (
            <div
              key={`${file.name}-${i}`}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs" style={{ background: "var(--bone)", color: "var(--ink)" }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
                <path d="M3.5 2A1.5 1.5 0 0 0 2 3.5v9A1.5 1.5 0 0 0 3.5 14h9a1.5 1.5 0 0 0 1.5-1.5v-7A1.5 1.5 0 0 0 12.5 5H10a1 1 0 0 1-1-1V1.5A1.5 1.5 0 0 0 7.5 0h-4A1.5 1.5 0 0 0 2 1.5v1" />
              </svg>
              <span className="max-w-[150px] truncate">{file.name}</span>
              <button
                type="button"
                onClick={() => removeFile(i)}
                className="ml-1 hover:opacity-70" style={{ color: "var(--warm-grau)" }}
              >
                &times;
              </button>
            </div>
          ))}
          {pendingReads > 0 && (
            <div className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs" style={{ background: "var(--bone)", color: "var(--terracotta)" }}>
              <span className="h-3 w-3 animate-spin rounded-full" style={{ border: "2px solid var(--warm-grau)", borderTopColor: "var(--terracotta)" }} />
              {pendingReads === 1 ? "Datei wird geladen..." : `${pendingReads} Dateien werden geladen...`}
            </div>
          )}
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* File upload button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl disabled:opacity-50" style={{ color: "var(--warm-grau)" }}
          title="Datei anhängen (PDF, Bild)"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
            <path fillRule="evenodd" d="M15.621 4.379a3 3 0 0 0-4.242 0l-7 7a3 3 0 0 0 4.241 4.243l7.07-7.071a1 1 0 0 1 1.415 1.414l-7.071 7.071a5 5 0 0 1-7.071-7.07l7-7.001a3 3 0 1 1 4.242 4.243L6.02 13.544a1 1 0 1 1-1.414-1.414l7.07-7.071a1 1 0 0 0 0-1.414Z" clipRule="evenodd" />
          </svg>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.csv,.xlsx,.xls,image/*,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          multiple
          className="hidden"
        />

        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Schreib Gridbert eine Nachricht..."
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border px-4 py-2.5 text-sm focus:outline-none disabled:opacity-50"
          style={{ borderColor: "var(--warm-grau)", background: "var(--kreide)" }}
          onFocus={(e) => { e.currentTarget.style.borderColor = "var(--terracotta)"; e.currentTarget.style.boxShadow = "0 0 0 1px var(--terracotta)"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = "var(--warm-grau)"; e.currentTarget.style.boxShadow = "none"; }}
        />
        <button
          type="submit"
          disabled={disabled || !filesReady || (!text.trim() && files.length === 0)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-white disabled:opacity-50"
          style={{ background: "var(--terracotta)" }}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5">
            <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95l14.095-5.638a.75.75 0 0 0 0-1.398L3.105 2.288Z" />
          </svg>
        </button>
      </div>
    </form>
  );
}
