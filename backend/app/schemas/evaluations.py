from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationRunSummary(BaseModel):
    run_id: UUID
    status: str
    suite_name: str
    suite_version: str | None
    model: str
    analysis_depth: str | None
    answer_detail: str | None
    trigger_source: str
    environment: str | None
    selected_case_count: int
    attempted_case_count: int
    completed_case_count: int
    passed_case_count: int
    failed_case_count: int
    error_case_count: int
    pass_rate_percent: float | None
    average_score_percent: float | None
    actual_cost_usd: float | None
    average_latency_ms: int | None
    p95_latency_ms: int | None
    total_tokens: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class EvaluationCategorySummary(BaseModel):
    category: str
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate_percent: float
    average_score_percent: float


class EvaluationCaseSummary(BaseModel):
    case_id: str
    category: str
    attempt_number: int
    status: str
    passed: bool | None
    score_percent: float | None
    tools_used: list[str]
    tool_call_count: int
    guardrail_status: str | None
    latency_ms: int | None
    cost_usd: float | None
    failed_checks: list[dict]
    error_stage: str | None
    error_type: str | None
    error_message: str | None


class EvaluationRunDetail(EvaluationRunSummary):
    cases: list[EvaluationCaseSummary]


class EvaluationDashboardResponse(BaseModel):
    generated_at: datetime
    latest_run: EvaluationRunSummary | None
    runs: list[EvaluationRunSummary]
    categories: list[EvaluationCategorySummary]
    total_runs: int
    completed_runs: int
    average_pass_rate_percent: float
    total_known_cost_usd: float


class EvaluationRunRequest(BaseModel):
    categories: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1, le=40)
    model: Literal["gpt-5.4", "gpt-4.1", "gpt-5.4-nano"] = "gpt-5.4-nano"
    analysis_depth: Literal["quick", "balanced", "deep"] = "quick"
    answer_detail: Literal["concise", "balanced", "detailed"] = "concise"
    budget_usd: float = Field(default=0.50, gt=0, le=5)
    estimated_cost_per_case: float = Field(default=0.10, gt=0, le=1)
    fail_fast: bool = False


class EvaluationRunQueued(BaseModel):
    run_id: UUID
    status: str
    selected_case_count: int
    estimated_cost_usd: float
