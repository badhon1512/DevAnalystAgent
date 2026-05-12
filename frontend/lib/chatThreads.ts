import type { ChatMessage, ChatThread } from "./types";
import { uuidv4 } from "./uuid";

const THREADS_KEY = "productai_threads_v1";
const ACTIVE_THREAD_KEY = "productai_active_thread_v1";

function buildWelcomeMessage(): ChatMessage {
  return {
    id: uuidv4(),
    role: "assistant",
    content:
      'Hi! I am ProductAI. Ask me about sales, stock, or returns (e.g., "Why did sales drop last week?").',
    createdAt: Date.now(),
  };
}

export function buildThreadTitle(text: string): string {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (!normalized) return "New chat";
  return normalized.length > 48 ? `${normalized.slice(0, 48)}...` : normalized;
}

export function createThread(): ChatThread {
  const now = Date.now();
  return {
    id: uuidv4(),
    title: "New chat",
    createdAt: now,
    updatedAt: now,
    messages: [buildWelcomeMessage()],
  };
}

export function readThreads(): ChatThread[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(THREADS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatThread[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveThreads(threads: ChatThread[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(THREADS_KEY, JSON.stringify(threads));
}

export function readActiveThreadId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_THREAD_KEY);
}

export function saveActiveThreadId(threadId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACTIVE_THREAD_KEY, threadId);
}

export function ensureThreads(): { threads: ChatThread[]; activeThreadId: string } {
  const existing = readThreads();
  const activeId = readActiveThreadId();

  if (existing.length === 0) {
    const thread = createThread();
    saveThreads([thread]);
    saveActiveThreadId(thread.id);
    return { threads: [thread], activeThreadId: thread.id };
  }

  const selected =
    (activeId && existing.find((thread) => thread.id === activeId)?.id) || existing[0].id;
  saveActiveThreadId(selected);
  return { threads: existing, activeThreadId: selected };
}
