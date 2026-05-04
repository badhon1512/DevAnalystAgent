"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { uuidv4 } from "../lib/uuid";
import type { ChatMessage } from "../lib/types";
import { sendChat } from "../lib/api";
import ChatMessageView from "./ChatMessage";
import ChatComposer from "./ChatComposer";

function getOrCreateConversationId(): string {
  const key = "productai_conversation_id";
  const existing = typeof window !== "undefined" ? localStorage.getItem(key) : null;
  if (existing) return existing;

  const id = uuidv4();
  if (typeof window !== "undefined") localStorage.setItem(key, id);
  return id;
}

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: uuidv4(),
      role: "assistant",
      content:
        "Hi! I’m ProductAI. Ask me about sales, stock, or returns (e.g., “Why did sales drop last week?”).",
      createdAt: Date.now(),
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  const conversationId = useMemo(
    () => (typeof window !== "undefined" ? getOrCreateConversationId() : "tmp"),
    []
  );

  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, loading]);

  async function handleSend(text: string) {
    setError("");

    const userMsg: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);

    const typingId = uuidv4();
    setMessages((prev) => [
      ...prev,
      { id: typingId, role: "assistant", content: "Typing…", createdAt: Date.now() },
    ]);

    setLoading(true);
    try {
      const data = await sendChat(text, conversationId);

      const assistantText =
        data?.final_answer ??
        data?.finalAnswer ??
        data?.answer ??
        "Backend responded, but the response format is not ready yet.";

      setMessages((prev) =>
        prev.map((m) =>
          m.id === typingId ? { ...m, content: assistantText, trace: data?.trace } : m
        )
      );
    } catch (e: unknown) {
      setMessages((prev) => prev.filter((m) => m.id !== typingId));
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chatShell">
      <header className="chatHeader">
        <div className="chatTitle">ProductAI</div>
        <div className="chatSub">Agentic analyst for product sales & inventory</div>
      </header>

      <section className="chatBody">
        {messages.map((m) => (
          <ChatMessageView key={m.id} message={m} />
        ))}

        {error && <div className="errorBanner">{error}</div>}

        <div ref={bottomRef} />
      </section>

      <footer className="chatFooter">
        <ChatComposer onSend={handleSend} disabled={loading} />
        <div className="footerHint">Tip: Enter to send • Shift+Enter for a new line</div>
      </footer>
    </div>
  );
}
