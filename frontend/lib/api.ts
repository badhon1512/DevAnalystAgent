import type { ChatResponse, InventoryRow, ListResponse, Product } from "./types";

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

