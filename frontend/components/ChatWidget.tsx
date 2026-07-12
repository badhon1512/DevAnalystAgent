"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { uuidv4 } from "../lib/uuid";
import type { ChatMessage } from "../lib/types";
import { sendChat } from "../lib/api";
import MarkdownContent from "./MarkdownContent";

type Props = {
  pageContext?: string; // optional: "/products", "/inventory", etc.
};

const STORAGE_KEY = "productai_chat_v1";

function ChatBubbleIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6A8.4 8.4 0 0 1 12.5 3H13a8 8 0 0 1 8 8v.5z" />
      <path d="M8 10h8" />
      <path d="M8 14h5" />
    </svg>
  );
}

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
    return `ProductAI Assistant - ${pageContext}`;
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
          width: 58,
          height: 58,
          borderRadius: 999,
          border: "1px solid rgba(45,212,191,0.42)",
          background:
            "radial-gradient(circle at 35% 25%, rgba(204,251,241,0.22), transparent 34%), linear-gradient(135deg, rgba(20,184,166,0.96), rgba(37,99,235,0.92))",
          boxShadow: "0 18px 44px rgba(20,184,166,0.26), 0 0 0 7px rgba(45,212,191,0.08)",
          color: "#f8fafc",
          fontWeight: 900,
          letterSpacing: "0.02em",
          cursor: "pointer",
          zIndex: 9999,
        }}
        title="Chat"
      >
        <ChatBubbleIcon />
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
            borderRadius: 18,
            border: "1px solid rgba(45,212,191,0.18)",
            background:
              "linear-gradient(155deg, rgba(15,23,42,0.98), rgba(2,6,23,0.94)), radial-gradient(circle at 20% 0%, rgba(20,184,166,0.16), transparent 48%)",
            boxShadow: "0 28px 80px rgba(0,0,0,0.58), 0 0 44px rgba(20,184,166,0.12)",
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
              borderBottom: "1px solid rgba(45,212,191,0.14)",
              background: "linear-gradient(90deg, rgba(20,184,166,0.14), rgba(15,23,42,0.82))",
            }}
          >
            <div>
              <div style={{ fontWeight: 900, fontSize: 13, color: "#f8fafc" }}>{headerTitle}</div>
              <div style={{ color: "#99f6e4", fontSize: 11, marginTop: 3 }}>
                Agentic answers, tools, traces, and actions
              </div>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <Link
                href="/chat"
                style={{
                  borderRadius: 10,
                  padding: "6px 10px",
                  border: "1px solid rgba(45,212,191,0.18)",
                  background: "rgba(20,184,166,0.12)",
                  color: "#ccfbf1",
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 800,
                  textDecoration: "none",
                }}
                title="Open AI workspace"
              >
                Open workspace
              </Link>
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
                x
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
                Try an AI task:
                <div style={{ marginTop: 8 }}>
                  - Find inventory risk from recent sales <br />
                  - Generate a demand outlook report <br />
                  - Compare products with RAG context
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
                Thinking...
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
              placeholder="Type a message..."
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
