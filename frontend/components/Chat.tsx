"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  deleteConversation,
  getConversationForUser,
  listConversations,
  sendChat,
  transcribeVoice,
} from "../lib/api";
import { buildThreadTitle } from "../lib/chatThreads";
import { DEMO_QUERIES } from "../lib/demoQueries";
import type { ChatMessage, ChatThread } from "../lib/types";
import { uuidv4 } from "../lib/uuid";
import ChatComposer from "./ChatComposer";
import ChatMessageView from "./ChatMessage";
import UsernameGate from "./UsernameGate";

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

function readStoredUsername() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("productai-username") || "";
}

export default function Chat() {
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(() => readStoredUsername());
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState("");
  const [activeMessages, setActiveMessages] = useState<ChatMessage[]>([]);
  const [activeTitle, setActiveTitle] = useState("ProductAI");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (username === null) {
      const savedUsername = readStoredUsername() || "";
      setUsername(savedUsername);
      if (!savedUsername) setInitializing(false);
    } else if (!username) {
      setInitializing(false);
    }
  }, [username]);

  useEffect(() => {
    if (!username) return;
    const activeUsername = username;
    async function loadInitialData() {
      try {
        const existingThreads = await listConversations(activeUsername);
        if (existingThreads.length === 0) {
          const newThread = await createConversation("New chat", activeUsername);
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
  }, [username]);

  useEffect(() => {
    async function loadThread() {
      if (!activeThreadId || !username) return;
      const activeUsername = username;
      try {
        const thread = await getConversationForUser(activeThreadId, activeUsername);
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
  }, [activeThreadId, username]);

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
    setHistoryOpen(false);
  }

  function handleSwitchUser() {
    localStorage.removeItem("productai-username");
    setUsername("");
    setThreads([]);
    setActiveThreadId("");
    setActiveMessages([]);
    setActiveTitle("ProductAI");
    setError("");
    setInitializing(false);
    router.push("/");
  }

  async function handleNewThread() {
    if (!username) return;
    const activeUsername = username;
    setError("");
    try {
      const thread = await createConversation("New chat", activeUsername);
      setThreads((current) => [thread, ...current]);
      setActiveThreadId(thread.id);
      setActiveTitle(thread.title);
      setActiveMessages([buildWelcomeMessage()]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create chat");
    }
  }

  async function handleDeleteThread(threadId: string) {
    if (!username) return;
    const activeUsername = username;
    setError("");
    try {
      await deleteConversation(threadId, activeUsername);
      const remaining = threads.filter((thread) => thread.id !== threadId);
      if (remaining.length === 0) {
        const replacement = await createConversation("New chat", activeUsername);
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
    if (!activeThreadId || !username) return;
    const activeUsername = username;
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
      const data = await sendChat(text, activeThreadId, activeUsername);
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

  if (!username) {
    if (username === null) {
      return (
        <div className="chatWorkspace userSetupWorkspace">
          <section className="userSetupPanel userSetupLoading">
            <div className="userSetupIntro">
              <div className="userSetupBrand">
                <span>AI</span>
                <strong>ProductAI</strong>
              </div>
              <p className="userSetupEyebrow">Preparing workspace</p>
              <h1>Loading your AI workspace</h1>
            </div>
          </section>
        </div>
      );
    }

    return <UsernameGate onResolved={setUsername} submitLabel="Continue to chat" />;
  }

  return (
    <div className="chatWorkspace">
      <nav className="chatTopNav">
        <Link className="chatTopBrand" href="/">
          <span>AI</span>
          ProductAI
        </Link>
        <div className="chatTopLinks">
          <Link href="/merchant">Merchant Portal</Link>
          <span className="chatTopLinkDisabled" aria-disabled="true" title="Storefront view is coming soon">
            Storefront view - coming soon
          </span>
          <button className="chatUserButton" type="button" onClick={handleSwitchUser}>
            @{username}
          </button>
        </div>
      </nav>

      {historyOpen && (
        <button
          className="threadMobileBackdrop"
          aria-label="Close conversation history"
          onClick={() => setHistoryOpen(false)}
          type="button"
        />
      )}

      <aside className={`threadSidebar${historyOpen ? " threadSidebarOpen" : ""}`}>
        <div className="threadSidebarHeader">
          <div>
            <div className="threadSidebarTitle">Conversation History</div>
            <div className="threadSidebarSub">Saved analysis threads and agent sessions</div>
          </div>
          <button className="threadNewButton" onClick={handleNewThread} type="button">
            New chat
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
          <button
            className="chatHistoryToggle"
            aria-label="Open conversation history"
            onClick={() => setHistoryOpen(true)}
            type="button"
          >
            <span />
            <span />
            <span />
          </button>
          <div className="chatTitle">{activeTitle}</div>
          <div className="chatSub">Ask ProductAI to analyze business data, call tools, create reports, and explain every action with traces and guardrails.</div>
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
            suggestions={DEMO_QUERIES}
          />
          <div className="footerHint">
            Use natural language or voice. ProductAI can research demand, inspect data, run tools,
            visualize insights, and summarize actions with cost and trace details.
          </div>
        </footer>
      </div>
    </div>
  );
}
