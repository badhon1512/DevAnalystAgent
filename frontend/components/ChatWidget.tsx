"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { uuidv4 } from "../lib/uuid";
import type { ChatMessage } from "../lib/types";
import { sendChat } from "../lib/api";
import MarkdownContent from "./MarkdownContent";

type Props = {
  pageContext?: string; // optional: "/products", "/inventory", etc.
};

const STORAGE_KEY = "productai_chat_v1";

function formatCost(cost?: number | null) {
  if (cost == null) return "n/a";
  return `$${cost.toFixed(6)}`;
}

function formatSeconds(ms: number) {
  return `${(ms / 1000).toFixed(2)}s`;
}

function renderTraceSummary(message: ChatMessage) {
  if (message.role === "user" || !message.trace) return null;

  const trace = message.trace;
  const toolCount = trace.tools_used.length || 0;

  return (
    <details
      style={{
        marginTop: 8,
        paddingTop: 8,
        borderTop: "1px solid rgba(255,255,255,0.10)",
        color: "#94a3b8",
        fontSize: 11,
      }}
    >
      <summary
        style={{
          cursor: "pointer",
          listStyle: "none",
          color: "#cbd5e1",
          fontWeight: 700,
        }}
      >
        Agent trace - {toolCount} tools - {formatSeconds(trace.latency_ms)}
      </summary>
      <div
        style={{
          marginTop: 8,
          display: "grid",
          gridTemplateColumns: "64px minmax(0, 1fr)",
          gap: "5px 8px",
          wordBreak: "break-word",
        }}
      >
        <span>Model</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>{trace.model}</strong>
        <span>Guard</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>{trace.guardrail_status}</strong>
        <span>Trace</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {trace.trace_id.slice(0, 8)}
        </strong>
        <span>In tok</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {trace.token_usage?.input_tokens ?? 0}
        </strong>
        <span>Out tok</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {trace.token_usage?.output_tokens ?? 0}
        </strong>
        <span>Total tok</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {trace.token_usage?.total_tokens ?? 0}
        </strong>
        <span>In cost</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {formatCost(trace.token_usage?.estimated_input_cost_usd)}
        </strong>
        <span>Out cost</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {formatCost(trace.token_usage?.estimated_output_cost_usd)}
        </strong>
        <span>Total</span>
        <strong style={{ color: "#e2e8f0", fontWeight: 700 }}>
          {formatCost(trace.token_usage?.estimated_total_cost_usd)}
        </strong>
      </div>
      {trace.tool_calls.length > 0 && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {trace.tool_calls.map((tool, index) => (
            <div
              key={`${tool.name}-${index}`}
              style={{
                padding: 8,
                borderRadius: 8,
                background: "rgba(2,6,23,0.28)",
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <div style={{ color: "#e2e8f0", fontWeight: 700 }}>{tool.name}</div>
              {tool.result_preview && (
                <div style={{ marginTop: 4, maxHeight: 52, overflow: "hidden" }}>
                  {tool.result_preview}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </details>
  );
}

export default function ChatWidget({ pageContext }: Props) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const listRef = useRef<HTMLDivElement | null>(null);

  // load persisted chat
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setMessages(JSON.parse(raw));
    } catch {
      // ignore
    }
  }, []);

  // persist chat
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch {
      // ignore
    }
  }, [messages]);

  // ESC to close
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // auto scroll to bottom
  useEffect(() => {
    if (!open) return;
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [open, messages.length]);

  const headerTitle = useMemo(() => {
    if (!pageContext) return "ProductAI Assistant";
    return `ProductAI Assistant • ${pageContext}`;
  }, [pageContext]);

  async function onSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };

    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const reply = await sendChat(input, "y");
      console.log("Received reply:", reply);

      const assistantMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: reply.answer || "Sorry, I have no response.",
        trace: reply.trace,
        createdAt: Date.now(),
      };

      setMessages((m) => [...m, assistantMsg]);
    } catch (e: unknown) {
      const assistantMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: `Sorry - I couldn't reach the agent API. (${
          e instanceof Error ? e.message : "error"
        })`,
        createdAt: Date.now(),
      };
      setMessages((m) => [...m, assistantMsg]);
    } finally {
      setLoading(false);
    }
  }

  function clearChat() {
    setMessages([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Open chat"
        style={{
          position: "fixed",
          right: 18,
          bottom: 18,
          width: 54,
          height: 54,
          borderRadius: 999,
          border: "1px solid rgba(255,255,255,0.14)",
          background: "rgba(37,99,235,0.30)",
          boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
          color: "white",
          fontWeight: 800,
          cursor: "pointer",
          zIndex: 9999,
        }}
        title="Chat"
      >
        💬
      </button>

      {/* Panel */}
      {open && (
        <div
          style={{
            position: "fixed",
            right: 18,
            bottom: 84,
            width: 380,
            maxWidth: "calc(100vw - 36px)",
            height: 520,
            maxHeight: "calc(100vh - 140px)",
            borderRadius: 16,
            border: "1px solid rgba(255,255,255,0.12)",
            background: "rgba(2,6,23,0.92)",
            boxShadow: "0 20px 60px rgba(0,0,0,0.55)",
            overflow: "hidden",
            zIndex: 9999,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "12px 12px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderBottom: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(15,23,42,0.75)",
            }}
          >
            <div>
              <div style={{ fontWeight: 800, fontSize: 13 }}>{headerTitle}</div>
              <div style={{ color: "#94a3b8", fontSize: 11 }}>
                Ask about data, metrics, or actions
              </div>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={clearChat}
                style={{
                  borderRadius: 10,
                  padding: "6px 10px",
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(2,6,23,0.35)",
                  color: "white",
                  cursor: "pointer",
                  fontSize: 12,
                }}
                title="Clear chat"
              >
                Clear
              </button>
              <button
                onClick={() => setOpen(false)}
                style={{
                  borderRadius: 10,
                  padding: "6px 10px",
                  border: "1px solid rgba(255,255,255,0.12)",
                  background: "rgba(2,6,23,0.35)",
                  color: "white",
                  cursor: "pointer",
                  fontSize: 12,
                }}
                title="Close"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            ref={listRef}
            style={{
              flex: 1,
              padding: 12,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            {messages.length === 0 && (
              <div style={{ color: "#94a3b8", fontSize: 13, lineHeight: 1.4 }}>
                Try:
                <div style={{ marginTop: 8 }}>
                  • “Show low-stock items in WH-MUC” <br />
                  • “Top 10 products by revenue last 30 days” <br />
                  • “Any unusual return reasons this week?”
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                  padding: "10px 12px",
                  borderRadius: 14,
                  background:
                    m.role === "user"
                      ? "rgba(37,99,235,0.30)"
                      : "rgba(148,163,184,0.12)",
                  border: "1px solid rgba(255,255,255,0.10)",
                  fontSize: 13,
                  lineHeight: 1.4,
                }}
              >
                <MarkdownContent content={m.content} />
                {renderTraceSummary(m)}
              </div>
            ))}

            {loading && (
              <div
                style={{
                  alignSelf: "flex-start",
                  maxWidth: "85%",
                  padding: "10px 12px",
                  borderRadius: 14,
                  background: "rgba(148,163,184,0.12)",
                  border: "1px solid rgba(255,255,255,0.10)",
                  color: "#cbd5e1",
                  fontSize: 13,
                }}
              >
                Thinking…
              </div>
            )}
          </div>

          {/* Composer */}
          <div
            style={{
              padding: 12,
              borderTop: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(15,23,42,0.65)",
              display: "flex",
              gap: 10,
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message…"
              onKeyDown={(e) => {
                if (e.key === "Enter") onSend();
              }}
              style={{
                flex: 1,
                padding: 10,
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(2,6,23,0.35)",
                color: "white",
              }}
            />
            <button
              onClick={onSend}
              disabled={loading}
              style={{
                padding: "0 14px",
                borderRadius: 12,
                border: "1px solid rgba(37,99,235,0.35)",
                background: "rgba(37,99,235,0.35)",
                color: "white",
                fontWeight: 800,
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}
