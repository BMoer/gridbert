import { useState } from "react";
import { Header } from "./Header";
import { Dashboard } from "../Dashboard/Dashboard";
import { ChatDrawer } from "../Chat/ChatDrawer";

export function MainLayout() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div style={{ minHeight: "100vh" }}>
      <Header onOpenChat={() => setChatOpen(true)} />
      <main style={{ padding: "1.5rem", maxWidth: "1280px", margin: "0 auto" }}>
        <Dashboard onOpenChat={() => setChatOpen(true)} />
      </main>
      <ChatDrawer open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  );
}
