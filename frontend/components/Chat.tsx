"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  sendChat,
  transcribeVoice,
} from "../lib/api";
import { buildThreadTitle } from "../lib/chatThreads";
import type { ChatMessage, ChatThread } from "../lib/types";
import { uuidv4 } from "../lib/uuid";
import ChatComposer from "./ChatComposer";
import ChatMessageView from "./ChatMessage";

function formatThreadTime(timestamp: number) {
  return new Date(timestamp).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

function buildWelcomeMessage(): ChatMessage {
  return {
    id: uuidv4(),
    role: "assistant",
    content:
      'Hi! I am ProductAI. Ask me about sales, stock, or returns (e.g., "Why did sales drop last week?").',
    createdAt: Date.now(),
  };
}

export default function Chat() {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [activeMessages, setActiveMessages] = useState<ChatMessage[]>([]);
  const [activeTitle, setActiveTitle] = useState("ProductAI");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    async function loadInitialData() {
      try {
        const existingThreads = await listConversations();
        if (existingThreads.length === 0) {
          const newThread = await createConversation("New chat");
          setThreads([newThread]);
          setActiveThreadId(newThread.id);
          setActiveTitle(newThread.title);
          setActiveMessages([buildWelcomeMessage()]);
        } else {
          setThreads(existingThreads);
          setActiveThreadId(existingThreads[0].id);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load conversations");
      } finally {
        setInitializing(false);
      }
    }

    void loadInitialData();
  }, []);

  useEffect(() => {
    async function loadThread() {
      if (!activeThreadId) return;
      try {
        const thread = await getConversation(activeThreadId);
        setActiveTitle(thread.title);
        setActiveMessages(
          thread.messages.length > 0 ? thread.messages : [buildWelcomeMessage()]
        );
        setThreads((current) =>
          current.map((item) =>
            item.id === thread.id
              ? {
                  ...item,
                  title: thread.title,
                  createdAt: thread.createdAt,
                  updatedAt: thread.updatedAt,
                  messages: thread.messages,
                }
              : item
          )
        );
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load conversation");
      }
    }

    void loadThread();
  }, [activeThreadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeMessages.length, loading, activeThreadId]);

  const sortedThreads = useMemo(
    () => [...threads].sort((a, b) => b.updatedAt - a.updatedAt),
    [threads]
  );

  function handleSelectThread(threadId: string) {
    setError("");
    setActiveThreadId(threadId);
  }

  async function handleNewThread() {
    setError("");
    try {
      const thread = await createConversation("New chat");
      setThreads((current) => [thread, ...current]);
      setActiveThreadId(thread.id);
      setActiveTitle(thread.title);
      setActiveMessages([buildWelcomeMessage()]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create chat");
    }
  }

  async function handleDeleteThread(threadId: string) {
    setError("");
    try {
      await deleteConversation(threadId);
      const remaining = threads.filter((thread) => thread.id !== threadId);
      if (remaining.length === 0) {
        const replacement = await createConversation("New chat");
        setThreads([replacement]);
        setActiveThreadId(replacement.id);
        setActiveTitle(replacement.title);
        setActiveMessages([buildWelcomeMessage()]);
      } else {
        setThreads(remaining);
        if (activeThreadId === threadId) {
          setActiveThreadId(remaining[0].id);
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete chat");
    }
  }

  async function handleSend(text: string) {
    if (!activeThreadId) return;
    setError("");

    const userMsg: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: text,
      createdAt: Date.now(),
    };

    setActiveMessages((current) => [...current, userMsg]);
    setThreads((current) =>
      current.map((thread) =>
        thread.id === activeThreadId
          ? {
              ...thread,
              title: thread.title === "New chat" ? buildThreadTitle(text) : thread.title,
              updatedAt: Date.now(),
            }
          : thread
      )
    );

    setLoading(true);
    try {
      const data = await sendChat(text, activeThreadId);
      const assistantText =
        data?.final_answer ??
        data?.finalAnswer ??
        data?.answer ??
        "Backend responded, but the response format is not ready yet.";

      const assistantMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: assistantText,
        createdAt: Date.now(),
        trace: data?.trace,
        report: data?.report,
      };

      setActiveMessages((current) => [...current, assistantMsg]);
      setActiveTitle((currentTitle) =>
        currentTitle === "New chat" ? buildThreadTitle(text) : currentTitle
      );
      setThreads((current) =>
        current.map((thread) =>
          thread.id === (data.conversation_id || activeThreadId)
            ? {
                ...thread,
                title: thread.title === "New chat" ? buildThreadTitle(text) : thread.title,
                updatedAt: Date.now(),
              }
            : thread
        )
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleTranscribeAudio(audio: Blob) {
    setError("");
    const result = await transcribeVoice(audio);
    return result.transcript;
  }

  return (
    <div className="chatWorkspace">
      <nav className="chatTopNav">
        <Link className="chatTopBrand" href="/">
          StoreWise AI
        </Link>
        <div className="chatTopLinks">
          <Link href="/storefront">Storefront</Link>
          <Link href="/merchant">Merchant Portal</Link>
        </div>
      </nav>

      <aside className="threadSidebar">
        <div className="threadSidebarHeader">
          <div>
            <div className="threadSidebarTitle">Chats</div>
            <div className="threadSidebarSub">Stored in the database by thread</div>
          </div>
          <button className="threadNewButton" onClick={handleNewThread} type="button">
            New
          </button>
        </div>
        <div className="threadList">
          {sortedThreads.map((thread) => (
            <div
              className={`threadListItem${
                thread.id === activeThreadId ? " threadListItemActive" : ""
              }`}
              key={thread.id}
            >
              <button
                className="threadSelectButton"
                onClick={() => handleSelectThread(thread.id)}
                type="button"
              >
                <div className="threadItemTitle">{thread.title}</div>
                <div className="threadItemMeta">{formatThreadTime(thread.updatedAt)}</div>
              </button>
              <button
                className="threadDeleteButton"
                onClick={() => void handleDeleteThread(thread.id)}
                title="Delete chat"
                type="button"
              >
                x
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="chatShell chatShellWide">
        <header className="chatHeader">
          <div className="chatTitle">{activeTitle}</div>
          <div className="chatSub">Agentic analyst for product sales & inventory</div>
        </header>

        <section className="chatBody">
          {initializing ? (
            <div className="msgRow msgRowAssistant">
              <div className="bubble bubbleAssistant">
                <div className="bubbleContent">Loading conversations...</div>
              </div>
            </div>
          ) : (
            activeMessages.map((message) => (
              <ChatMessageView key={message.id} message={message} />
            ))
          )}

          {loading && (
            <div className="msgRow msgRowAssistant">
              <div className="bubble bubbleAssistant">
                <div className="bubbleContent">Typing...</div>
              </div>
            </div>
          )}

          {error && <div className="errorBanner">{error}</div>}
          <div ref={bottomRef} />
        </section>

        <footer className="chatFooter">
          <ChatComposer
            onSend={handleSend}
            disabled={loading || initializing}
            onTranscribeAudio={handleTranscribeAudio}
            onVoiceError={setError}
          />
          <div className="footerHint">Tip: Enter to send - Shift+Enter for a new line</div>
        </footer>
      </div>
    </div>
  );
}
