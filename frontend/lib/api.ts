import type {
  ChatThread,
  ChatResponse,
  ChatMessage,
  AdminConversationDetail,
  AdminConversationSummary,
  DashboardAnalytics,
  EvaluationDashboard,
  EvaluationRunDetail,
  EvaluationRunQueued,
  EvaluationRunRequest,
  InventoryRow,
  ListResponse,
  PageViewStats,
  Product,
  ProductDetail,
  VoiceTranscriptionResponse,
  ChatOptions,
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


export async function sendChat(
  query: string,
  conversationId: string,
  username: string,
  options?: ChatOptions,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, conversation_id: conversationId, username, options }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error (${res.status}): ${text}`);
  }

  return res.json();
}

export async function resolveChatUser(username: string): Promise<{ user_id: string; username: string }> {
  const res = await fetch(`${API_BASE}/users/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Username setup failed (${res.status}): ${text}`);
  }

  return res.json();
}

export async function listConversations(username: string): Promise<ChatThread[]> {
  const conversations = await getJSON<
    {
      conversation_id: string;
      title: string;
      created_at: string;
      updated_at: string;
      message_count: number;
    }[]
  >(`${API_BASE}/conversations${buildQuery({ username })}`);

  return conversations.map((conversation) => ({
    id: conversation.conversation_id,
    title: conversation.title,
    createdAt: new Date(conversation.created_at).getTime(),
    updatedAt: new Date(conversation.updated_at).getTime(),
    messages: [],
  }));
}

export async function getConversationForUser(
  conversationId: string,
  username: string,
): Promise<ChatThread> {
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
  }>(`${API_BASE}/conversations/${conversationId}${buildQuery({ username })}`);

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

export async function createConversation(title: string | undefined, username: string): Promise<ChatThread> {
  const conversation = await fetch(`${API_BASE}/conversations${buildQuery({ username })}`, {
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

export async function deleteConversation(conversationId: string, username: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}${buildQuery({ username })}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error (${res.status}): ${text}`);
  }
}

export async function adminLogin(secret: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ secret, password }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Admin login failed (${res.status}): ${text}`);
  }

  const data = (await res.json()) as { token: string };
  return data.token;
}

function adminHeaders(token: string) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function fetchPageViewStats(
  token: string,
  days = 30,
  path?: string,
): Promise<PageViewStats> {
  return getJSONWithHeaders<PageViewStats>(
    `${API_BASE}/page-views/stats${buildQuery({ days, path })}`,
    adminHeaders(token),
  );
}

export async function adminListConversations(token: string): Promise<AdminConversationSummary[]> {
  return getJSONWithHeaders<AdminConversationSummary[]>(
    `${API_BASE}/admin/conversations?include_inactive=true`,
    adminHeaders(token),
  );
}

export async function adminGetConversation(
  token: string,
  conversationId: string,
): Promise<AdminConversationDetail> {
  return getJSONWithHeaders<AdminConversationDetail>(
    `${API_BASE}/admin/conversations/${conversationId}`,
    adminHeaders(token),
  );
}

export async function adminSetConversationActive(
  token: string,
  conversationId: string,
  isActive: boolean,
): Promise<AdminConversationSummary> {
  const res = await fetch(`${API_BASE}/admin/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      ...adminHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ is_active: isActive }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Admin update failed (${res.status}): ${text}`);
  }

  return res.json();
}

export async function adminDeleteConversation(token: string, conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/conversations/${conversationId}`, {
    method: "DELETE",
    headers: adminHeaders(token),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Admin delete failed (${res.status}): ${text}`);
  }
}

export async function getEvaluationDashboard(): Promise<EvaluationDashboard> {
  return getJSON<EvaluationDashboard>(`${API_BASE}/evaluations/dashboard`);
}

export async function getEvaluationRun(runId: string): Promise<EvaluationRunDetail> {
  return getJSON<EvaluationRunDetail>(`${API_BASE}/evaluations/runs/${runId}`);
}

export async function adminQueueEvaluation(
  token: string,
  payload: EvaluationRunRequest,
): Promise<EvaluationRunQueued> {
  const res = await fetch(`${API_BASE}/admin/evaluations`, {
    method: "POST",
    headers: {
      ...adminHeaders(token),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Evaluation could not be started (${res.status}): ${text}`);
  }

  return res.json();
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

async function getJSONWithHeaders<T>(url: string, headers: Record<string, string>): Promise<T> {
  const res = await fetch(url, { cache: "no-store", headers });
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
  dashboard: () => getJSON<DashboardAnalytics>(`${API_BASE}/analytics/dashboard`),

  products: (q?: { search?: string; category?: string; brand?: string; limit?: number; offset?: number }) =>
    getJSON<ListResponse<Product>>(`${API_BASE}/products${buildQuery(q || {})}`),

  product: (productId: string) =>
    getJSON<ProductDetail>(`${API_BASE}/products/${productId}`),

  warehouses: (q?: { search?: string; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/warehouses${buildQuery(q || {})}`),

  inventory: (q?: { search?: string; warehouse_code?: string; low_stock?: 0 | 1; limit?: number; offset?: number }) =>
    getJSON<ListResponse<InventoryRow>>(`${API_BASE}/inventory${buildQuery(q || {})}`),

  sales: (q?: { search?: string; channel?: string; region?: string; days?: number; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/sales${buildQuery(q || {})}`),

  returns: (q?: { search?: string; days?: number; limit?: number; offset?: number }) =>
    getJSON(`${API_BASE}/returns${buildQuery(q || {})}`),
};

