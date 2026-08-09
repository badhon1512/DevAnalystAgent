from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RagQueryStyle = Literal[
    "direct",
    "conversational",
    "implicit",
    "complex",
    "noisy",
]


ChatModel = Literal["gpt-5.4", "gpt-4.1", "gpt-5.4-nano"]
AnalysisDepth = Literal["quick", "balanced", "deep"]
AnswerDetail = Literal["concise", "balanced", "detailed"]


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_tools: list[str]
    forbidden_tools: list[str]
    expected_answer_contains: list[str]
    expected_answer_terms: list[list[str]] = Field(default_factory=list)
    reference_source: str = Field(min_length=1)
    max_tool_calls: int = Field(ge=0)


class EvalOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: ChatModel = "gpt-5.4"
    analysis_depth: AnalysisDepth = "balanced"
    answer_detail: AnswerDetail = "balanced"


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str


class BenchmarkScore(BaseModel):
    case_id: str
    passed: bool
    score_percent: int = Field(ge=0, le=100)
    checks: list[CheckResult]


class RagBenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    query: str = Field(min_length=1)
    query_style: RagQueryStyle
    top_k: int = Field(default=5, ge=1, le=12)
    expected_sources: list[str] = Field(min_length=1)
    expected_content_term_groups: list[list[str]] = Field(default_factory=list)
    minimum_matches: int = Field(default=1, ge=1)
    maximum_relevant_rank: int = Field(default=5, ge=1)
    maximum_latency_ms: int = Field(default=3000, ge=1)


class RagQrel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    passage_key: str = Field(min_length=1)
    chunk_text: str = Field(min_length=1)
    relevance: int = Field(ge=1, le=2)


class RagAtKMetrics(BaseModel):
    k: int = Field(ge=1)
    result_count: int = Field(ge=0)
    relevant_result_count: int = Field(ge=0)
    hit: bool
    precision_percent: float = Field(ge=0, le=100)
    passage_recall_percent: float = Field(ge=0, le=100)
    source_recall_percent: float = Field(ge=0, le=100)
    retrieval_f1_percent: float = Field(ge=0, le=100)
    reciprocal_rank: float = Field(ge=0, le=1)
    average_precision: float = Field(ge=0, le=1)
    ndcg: float = Field(ge=0, le=1)
    content_term_recall_percent: float = Field(ge=0, le=100)
    context_character_count: int = Field(ge=0)


class RagBenchmarkMetrics(BaseModel):
    retrieval_mode: Literal["vector", "keyword", "hybrid"]
    result_count: int = Field(ge=0)
    relevant_result_count: int = Field(ge=0)
    hit_at_k: bool
    hit_at_1: bool
    hit_at_3: bool
    precision_at_k_percent: float = Field(ge=0, le=100)
    passage_recall_percent: int = Field(ge=0, le=100)
    source_recall_percent: int = Field(ge=0, le=100)
    retrieval_f1_percent: float = Field(ge=0, le=100)
    reciprocal_rank: float = Field(ge=0, le=1)
    mean_average_precision: float = Field(ge=0, le=1)
    ndcg_at_k: float = Field(ge=0, le=1)
    content_term_recall_percent: int = Field(ge=0, le=100)
    duplicate_chunk_count: int = Field(ge=0)
    redundancy_percent: float = Field(ge=0, le=100)
    unique_chunk_ratio_percent: float = Field(ge=0, le=100)
    mean_similarity_score: float
    context_character_count: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    metrics_by_k: dict[str, RagAtKMetrics]


class RagBenchmarkScore(BaseModel):
    case_id: str
    passed: bool
    score_percent: int = Field(ge=0, le=100)
    checks: list[CheckResult]
    metrics: RagBenchmarkMetrics
