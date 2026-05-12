import type {
  ChatThread,
  ChatResponse,
  ChatMessage,
  InventoryRow,
  ListResponse,
  Product,
  VoiceTranscriptionResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function callCompute(x: number, y: number) {
  const res = await fetch(`${API_BASE}/compute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x, y }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error: ${res.status} ${text}`);
  }

  return res.json();
}


export async function sendChat(query: string, conversationId: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error (${res.status}): ${text}`);
  }

  return res.json();
}

export async function listConversations(): Promise<ChatThread[]> {
  const conversations = await getJSON<
    {
      conversation_id: string;
      title: string;
      created_at: string;
      updated_at: string;
      message_count: number;
    }[]
  >(`${API_BASE}/conversations`);

  return conversations.map((conversation) => ({
    id: conversation.conversation_id,
    title: conversation.title,
    createdAt: new Date(conversation.created_at).getTime(),
    updatedAt: new Date(conversation.updated_at).getTime(),
    messages: [],
  }));
}

export async function getConversation(conversationId: string): Promise<ChatThread> {
  const conversation = await getJSON<{
    conversation_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    messages: Array<{
      message_id: string;
      role: "user" | "assistant";
      content: string;
      created_at: string;
      trace?: ChatMessage["trace"];
      report?: ChatMessage["report"];
    }>;
  }>(`${API_BASE}/conversations/${conversationId}`);

  return {
    id: conversation.conversation_id,
    title: conversation.title,
    createdAt: new Date(conversation.created_at).getTime(),
    updatedAt: new Date(conversation.updated_at).getTime(),
    messages: conversation.messages.map((message) => ({
      id: message.message_id,
      role: message.role,
      content: message.content,
      createdAt: new Date(message.created_at).getTime(),
      trace: message.trace,
      report: message.report,
    })),
  };
}

export async function createConversation(title?: string): Promise<ChatThread> {
  const conversation = await fetch(`${API_BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

  if (!conversation.ok) {
    const text = await conversation.text();
    throw new Error(`Backend error (${conversation.status}): ${text}`);
  }

  const data = (await conversation.json()) as {
    conversation_id: string;
    title: string;
    created_at: string;
    updated_at: string;
  };

  return {
    id: data.conversation_id,
    title: data.title,
    createdAt: new Date(data.created_at).getTime(),
    updatedAt: new Date(data.updated_at).getTime(),
    messages: [],
  };
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error (${res.status}): ${text}`);
  }
}

export async function transcribeVoice(audio: Blob): Promise<VoiceTranscriptionResponse> {
  const form = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : "webm";
  form.append("file", audio, `recording.${extension}`);

  const res = await fetch(`${API_BASE}/voice/transcribe`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Voice transcription error (${res.status}): ${text}`);
  }

  return res.json();
}




async function getJSON<T>(url: string): Promise<T> {
  console.log("FETCH URL:", url);
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error (${res.status}): ${text}`);
  }
  return res.json();
}

export function buildQuery(params: Record<string, string | number | undefined>) {
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") usp.set(k, String(v));
  });
  const qs = usp.toString();
  return qs ? `?${qs}` : "";
}

// ---- table endpoints (we’ll implement on backend soon) ----
export const api = {
  products: (q?: { search?: string; category?: string; brand?: string; limit?: number; offset?: number }) =>
    getJSON<ListResponse<Product>>(`${API_BASE}/products${buildQuery(q || {})}`),

  warehouses: (q?: { search?: string; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/warehouses${buildQuery(q || {})}`),

  inventory: (q?: { search?: string; warehouse_code?: string; low_stock?: 0 | 1; limit?: number; offset?: number }) =>
    getJSON<ListResponse<InventoryRow>>(`${API_BASE}/inventory${buildQuery(q || {})}`),

  sales: (q?: { search?: string; channel?: string; region?: string; days?: number; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/sales${buildQuery(q || {})}`),

  returns: (q?: { search?: string; days?: number; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/returns${buildQuery(q || {})}`),
};

