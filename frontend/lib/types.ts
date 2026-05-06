export type Role = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  trace?: AgentTrace;
  report?: ReportSummary;
};

export type ChatResponse = {
  answer?: string;
  message_id?: string;
  final_answer?: string;
  finalAnswer?: string;
  trace?: AgentTrace;
  report?: ReportSummary;
};

export type ReportAsset = {
  type: "html" | "markdown" | "json" | "pdf" | "chart" | "csv" | "other";
  label: string;
  filename: string;
  relative_path: string;
  content_type: string;
  view_url?: string | null;
  download_url?: string | null;
};

export type ReportSummary = {
  report_id: string;
  title: string;
  summary: string;
  created_at: string;
  trace_id?: string | null;
  assets: ReportAsset[];
};

export type VoiceTranscriptionResponse = {
  transcript: string;
  model: string;
  latency_ms: number;
};

export type ToolCallTrace = {
  name: string;
  args: Record<string, unknown>;
  result_preview?: string | null;
  artifacts?: {
    type: string;
    label: string;
    filename: string;
    content_type: string;
    view_url?: string | null;
    download_url?: string | null;
  }[];
};

export type AgentTrace = {
  trace_id: string;
  conversation_id: string;
  latency_ms: number;
  guardrail_status: string;
  model: string;
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated_input_cost_usd?: number | null;
    estimated_output_cost_usd?: number | null;
    estimated_total_cost_usd?: number | null;
  };
  tools_used: string[];
  tool_calls: ToolCallTrace[];
  message_count: number;
};

export type Product = {
  product_id: string;
  sku: string;
  name: string;
  category?: string | null;
  brand?: string | null;
  currency: string;
  price: string | number;
  cost?: string | number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type Warehouse = {
  warehouse_id: string;
  code: string;
  name: string;
  city?: string | null;
  country?: string | null;
  created_at: string;
  updated_at: string;
};

export type InventoryRow = {
  inventory_id: string;
  sku: string;
  product_name: string;
  warehouse_name: string;
  stock_on_hand: number;
  reorder_point: number;
  updated_at: string;
};

export type SaleRow = {
  sale_id: string;
  sold_at: string;
  sku: string;
  product_name: string;
  quantity: number;
  unit_price: string | number;
  revenue: string | number;
  channel: "online" | "retail" | "b2b";
  region?: string | null;
};

export type ReturnRow = {
  return_id: string;
  returned_at: string;
  sku: string;
  product_name: string;
  quantity: number;
  reason?: string | null;
};

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

