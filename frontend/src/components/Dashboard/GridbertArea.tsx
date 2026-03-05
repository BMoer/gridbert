import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatStore } from "../../stores/chatStore";

interface Props {
  onOpenChat: () => void;
}

export function GridbertArea({ onOpenChat }: Props) {
  const messages = useChatStore((s) => s.messages);

  // Find latest assistant message for speech bubble
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.content);
  const bubbleContent = lastAssistant?.content ?? null;
  const defaultGreeting = "Leg deine Unterlagen auf den Tisch — ich schau mir das an.";

  return (
    <div
      style={{
        gridArea: "gridbert",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
        padding: "1.5rem",
        background: "transparent",
        boxShadow: "none",
        animation: "fadeInUp 0.5s ease-out 0.2s backwards",
      }}
    >
      {/* Speech bubble — clickable to open chat */}
      <div
        onClick={onOpenChat}
        style={{
          background: "var(--kreide)",
          border: "1.5px solid var(--ink)",
          borderRadius: "var(--radius-lg)",
          padding: "1rem 1.25rem",
          boxShadow: "var(--shadow-floating)",
          fontFamily: "var(--font-body)",
          fontSize: "0.9rem",
          lineHeight: 1.5,
          color: "var(--ink)",
          position: "relative",
          maxWidth: "280px",
          maxHeight: "240px",
          overflowY: "auto",
          cursor: "pointer",
          animation: "bubbleIn 0.3s ease-out 0.6s backwards",
        }}
      >
        {bubbleContent ? (
          <div className="prose prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_table]:block [&_table]:overflow-x-auto [&_table]:text-xs">
            <Markdown remarkPlugins={[remarkGfm]}>{bubbleContent}</Markdown>
          </div>
        ) : (
          <span style={{ fontStyle: "italic", opacity: 0.8 }}>{defaultGreeting}</span>
        )}
        {/* Triangle pointer */}
        <span
          style={{
            position: "absolute",
            bottom: -10,
            left: "50%",
            transform: "translateX(-50%)",
            width: 0,
            height: 0,
            borderLeft: "10px solid transparent",
            borderRight: "10px solid transparent",
            borderTop: "10px solid var(--ink)",
          }}
        />
        <span
          style={{
            position: "absolute",
            bottom: -8,
            left: "50%",
            transform: "translateX(-50%)",
            width: 0,
            height: 0,
            borderLeft: "9px solid transparent",
            borderRight: "9px solid transparent",
            borderTop: "9px solid var(--kreide)",
          }}
        />
      </div>

      {/* Gridbert SVG Avatar */}
      <svg
        width="130"
        height="160"
        viewBox="0 0 130 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ flexShrink: 0 }}
      >
        <g style={{ animation: "gentleBob 3s ease-in-out infinite" }}>
          {/* Body */}
          <rect x="25" y="30" width="80" height="80" rx="10" stroke="#2C2C2C" strokeWidth="2.5" fill="var(--kreide)" />
          {/* Glasses */}
          <circle cx="50" cy="62" r="14" stroke="#2C2C2C" strokeWidth="2" fill="none" />
          <circle cx="80" cy="62" r="14" stroke="#2C2C2C" strokeWidth="2" fill="none" />
          <path d="M64,60 Q65,56 66,60" stroke="#2C2C2C" strokeWidth="1.8" fill="none" />
          <line x1="36" y1="60" x2="25" y2="56" stroke="#2C2C2C" strokeWidth="1.8" strokeLinecap="round" />
          <line x1="94" y1="60" x2="105" y2="56" stroke="#2C2C2C" strokeWidth="1.8" strokeLinecap="round" />
          {/* Eyes */}
          <g style={{ animation: "blink 4s ease-in-out infinite", transformOrigin: "65px 62px" }}>
            <circle cx="50" cy="61" r="3" fill="#2C2C2C" />
            <circle cx="80" cy="61" r="3" fill="#2C2C2C" />
            <circle cx="51.5" cy="59.5" r="1" fill="var(--kreide)" />
            <circle cx="81.5" cy="59.5" r="1" fill="var(--kreide)" />
          </g>
          {/* Mouth */}
          <path d="M58,78 Q65,84 72,78" stroke="#2C2C2C" strokeWidth="1.5" fill="none" strokeLinecap="round" />
          {/* Bow-tie */}
          <polygon points="55,112 65,107 65,117" fill="#C4654A" stroke="#2C2C2C" strokeWidth="1" />
          <polygon points="75,112 65,107 65,117" fill="#C4654A" stroke="#2C2C2C" strokeWidth="1" />
          <circle cx="65" cy="112" r="2.5" fill="#2C2C2C" />
          {/* Legs */}
          <line x1="50" y1="110" x2="45" y2="140" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          <line x1="80" y1="110" x2="85" y2="140" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          <line x1="45" y1="140" x2="38" y2="140" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          <line x1="85" y1="140" x2="92" y2="140" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          {/* Arms */}
          <line x1="25" y1="70" x2="10" y2="50" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          <line x1="105" y1="70" x2="118" y2="55" stroke="#2C2C2C" strokeWidth="2" strokeLinecap="round" />
          <circle cx="118" cy="55" r="3" fill="none" stroke="#2C2C2C" strokeWidth="1.5" />
        </g>
      </svg>
    </div>
  );
}
