import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { ChatWindow } from "../Chat/ChatWindow";
import { DashboardGrid } from "../Dashboard/DashboardGrid";

export function MainLayout() {
  const [showDashboard, setShowDashboard] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        {/* Top bar with view toggle */}
        <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
          <h1 className="text-sm font-medium text-gray-600">
            {showDashboard ? "Dashboard" : "Chat"}
          </h1>
          <div className="flex rounded-lg bg-gray-100 p-0.5">
            <button
              onClick={() => setShowDashboard(false)}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                !showDashboard
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500"
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setShowDashboard(true)}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                showDashboard
                  ? "bg-white text-gray-800 shadow-sm"
                  : "text-gray-500"
              }`}
            >
              Dashboard
            </button>
          </div>
        </header>

        {/* Content area */}
        <main className="flex-1 overflow-hidden">
          {showDashboard ? (
            <div className="h-full overflow-y-auto p-6">
              <DashboardGrid />
            </div>
          ) : (
            <ChatWindow />
          )}
        </main>
      </div>
    </div>
  );
}
