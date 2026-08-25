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
  isActive?: boolean;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
};

export type AdminConversationSummary = {
  conversation_id: string;
  username?: string | null;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview?: string | null;
};

export type AdminConversationDetail = AdminConversationSummary & {
  messages: Array<{
    message_id: string;
    role: "user" | "assistant";
    content: string;
    created_at: string;
    trace?: AgentTrace | null;
    report?: ReportSummary | null;
  }>;
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

export type ChatOptions = {
  model: "openai/gpt-oss-120b" | "gpt-5.4" | "gpt-4.1" | "gpt-5.4-nano";
  analysis_depth: "quick" | "balanced" | "deep";
  answer_detail: "concise" | "balanced" | "detailed";
};

export const DEFAULT_CHAT_OPTIONS: ChatOptions = {
  model: "gpt-5.4",
  analysis_depth: "balanced",
  answer_detail: "balanced",
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
  result?: string | null;
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

export type DashboardMetric = {
  label: string;
  value: string | number;
  detail: string;
  tone: "good" | "warn" | "danger" | "neutral" | string;
};

export type RevenuePoint = {
  label: string;
  revenue: number;
};

export type CategoryDemand = {
  label: string;
  units: number;
  revenue: number;
  share: number;
};

export type BranchRisk = {
  branch: string;
  city?: string | null;
  stock_on_hand: number;
  reorder_point: number;
  coverage: number;
  low_stock_skus: number;
  risk: "High" | "Medium" | "Low" | string;
};

export type ProductInsight = {
  product_id: string;
  name: string;
  category?: string | null;
  units: number;
  revenue: number;
};

export type ChannelInsight = {
  channel: string;
  revenue: number;
  share: number;
};

export type ReturnInsight = {
  returned_units: number;
  sold_units: number;
  return_rate: number;
  top_reasons: DashboardMetric[];
};

export type DashboardAnalytics = {
  generated_at: string;
  metrics: DashboardMetric[];
  revenue_trend: RevenuePoint[];
  category_demand: CategoryDemand[];
  branch_risk: BranchRisk[];
  top_products: ProductInsight[];
  channel_mix: ChannelInsight[];
  returns: ReturnInsight;
};

export type EvaluationRunSummary = {
  run_id: string;
  status: string;
  suite_name: string;
  suite_version?: string | null;
  model: string;
  analysis_depth?: string | null;
  answer_detail?: string | null;
  trigger_source: string;
  environment?: string | null;
  selected_case_count: number;
  attempted_case_count: number;
  completed_case_count: number;
  passed_case_count: number;
  failed_case_count: number;
  error_case_count: number;
  pass_rate_percent?: number | null;
  average_score_percent?: number | null;
  actual_cost_usd?: number | null;
  average_latency_ms?: number | null;
  p95_latency_ms?: number | null;
  total_tokens: number;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
};

export type EvaluationCategorySummary = {
  category: string;
  total: number;
  passed: number;
  failed: number;
  errors: number;
  pass_rate_percent: number;
  average_score_percent: number;
};

export type EvaluationCaseSummary = {
  case_id: string;
  category: string;
  attempt_number: number;
  status: string;
  passed?: boolean | null;
  score_percent?: number | null;
  tools_used: string[];
  tool_call_count: number;
  guardrail_status?: string | null;
  latency_ms?: number | null;
  cost_usd?: number | null;
  failed_checks: Array<{ name?: string; detail?: string; passed?: boolean }>;
  error_stage?: string | null;
  error_type?: string | null;
  error_message?: string | null;
};

export type EvaluationRunDetail = EvaluationRunSummary & {
  cases: EvaluationCaseSummary[];
};

export type RagEvaluationSummary = {
  run_id: string;
  status: string;
  retrieval_mode: "keyword" | "vector" | "hybrid";
  embedding_model: string;
  embedding_provider: string;
  embedding_dimensions: number;
  selected_case_count: number;
  completed_case_count: number;
  pass_rate_percent: number;
  quality_gate_status: string;
  hit_at_1_percent: number;
  hit_at_3_percent: number;
  hit_at_k_percent: number;
  mean_precision_at_k_percent: number;
  mean_passage_recall_percent: number;
  mean_source_recall_percent: number;
  mean_retrieval_f1_percent: number;
  mean_reciprocal_rank: number;
  mean_average_precision: number;
  mean_ndcg_at_k: number;
  mean_content_term_recall_percent: number;
  mean_unique_chunk_ratio_percent: number;
  mean_redundancy_percent: number;
  mean_similarity_score: number;
  mean_context_character_count: number;
  error_free_rate_percent: number;
  average_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  throughput_cases_per_second: number;
  quality_gates: Record<string, boolean>;
  generation_evaluation: Record<string, string>;
  metrics_by_k: Record<string, {
    hit_percent: number;
    mean_precision_percent: number;
    mean_passage_recall_percent: number;
    mean_source_recall_percent: number;
    mean_retrieval_f1_percent: number;
    mean_reciprocal_rank: number;
    mean_average_precision: number;
    mean_ndcg: number;
  }>;
  finished_at?: string | null;
};

export type EvaluationDashboard = {
  generated_at: string;
  latest_run?: EvaluationRunSummary | null;
  runs: EvaluationRunSummary[];
  categories: EvaluationCategorySummary[];
  total_runs: number;
  completed_runs: number;
  average_pass_rate_percent: number;
  total_known_cost_usd: number;
  rag_latest?: RagEvaluationSummary | null;
};

export type EvaluationRunRequest = {
  categories?: string[];
  case_ids?: string[];
  limit?: number;
  model: ChatOptions["model"];
  analysis_depth: ChatOptions["analysis_depth"];
  answer_detail: ChatOptions["answer_detail"];
  budget_usd: number;
  estimated_cost_per_case: number;
  fail_fast: boolean;
};

export type EvaluationRunQueued = {
  run_id: string;
  status: string;
  selected_case_count: number;
  estimated_cost_usd: number;
};

export type RagEvaluationRunRequest = {
  categories?: string[];
  case_ids?: string[];
  limit?: number;
  fail_fast: boolean;
  retrieval_mode: "keyword" | "vector" | "hybrid";
  embedding_model: "BAAI/bge-small-en-v1.5" | "text-embedding-3-small";
};

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type CountBucket = {
  label: string;
  views: number;
};

export type DailyViews = {
  date: string;
  views: number;
  visitors: number;
};

export type RecentView = {
  viewed_at: string;
  path: string;
  country: string | null;
  city: string | null;
  referrer: string | null;
};

export type PageViewStats = {
  generated_at: string;
  window_days: number;
  total_views: number;
  unique_visitors: number;
  views_today: number;
  daily: DailyViews[];
  top_countries: CountBucket[];
  top_paths: CountBucket[];
  top_referrers: CountBucket[];
  recent: RecentView[];
};
