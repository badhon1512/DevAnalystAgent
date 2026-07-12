export type Role = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  trace?: AgentTrace;
  report?: ReportSummary;
};

export type ChatThread = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
};

export type ChatResponse = {
  conversation_id: string;
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
  category_id?: string | null;
  sku: string;
  name: string;
  slug?: string | null;
  short_description?: string | null;
  long_description?: string | null;
  category?: string | null;
  brand?: string | null;
  manufacturer?: string | null;
  model_number?: string | null;
  tags?: string[] | null;
  use_cases?: string[] | null;
  target_audience?: string | null;
  warranty_months?: number | null;
  return_window_days?: number | null;
  care_instructions?: string | null;
  compatibility_notes?: string | null;
  included_accessories?: string[] | null;
  safety_notes?: string | null;
  currency: string;
  price: string | number;
  cost?: string | number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductVariant = {
  variant_id: string;
  product_id: string;
  sku: string;
  title: string;
  color?: string | null;
  size?: string | null;
  material?: string | null;
  ram_gb?: number | null;
  storage_gb?: number | null;
  storage_type?: string | null;
  processor?: string | null;
  gpu?: string | null;
  display_size?: string | null;
  battery_life_hours?: string | number | null;
  option_values?: Record<string, string | number | boolean | null> | null;
  price: string | number;
  cost?: string | number | null;
  currency: string;
  barcode?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductImage = {
  image_id: string;
  product_id: string;
  variant_id?: string | null;
  url: string;
  alt_text?: string | null;
  position: number;
  is_primary: boolean;
};

export type ProductSpec = {
  spec_id: string;
  product_id: string;
  variant_id?: string | null;
  group_name: string;
  name: string;
  value: string;
  unit?: string | null;
  position: number;
};

export type ProductReview = {
  review_id: string;
  product_id: string;
  variant_id?: string | null;
  rating: number;
  title: string;
  body: string;
  sentiment?: string | null;
  created_at: string;
};

export type ProductDetail = Product & {
  variants: ProductVariant[];
  images: ProductImage[];
  specs: ProductSpec[];
  reviews: ProductReview[];
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

