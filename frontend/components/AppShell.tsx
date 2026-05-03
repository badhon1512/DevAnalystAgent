"use client";

import Sidebar from "./Sidebar";
import ChatWidget from "./ChatWidget";

export default function AppShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: 20 }}>
        <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 14 }}>{title}</div>
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 14,
            overflow: "hidden",
            background: "rgba(2,6,23,0.25)",
          }}
        >
          {children}
        </div>
        <ChatWidget pageContext={title} />
      </main>
    </div>
  );
}
