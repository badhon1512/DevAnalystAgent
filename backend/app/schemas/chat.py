from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.report import ReportSummary


class ToolArtifact(BaseModel):
    type: str
    label: str
    filename: str
    content_type: str
    view_url: str | None = None
    download_url: str | None = None


class ToolCallTrace(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    result_preview: str | None = None
    artifacts: list[ToolArtifact] = Field(default_factory=list)


class TokenUsageTrace(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_input_cost_usd: float | None = None
    estimated_output_cost_usd: float | None = None
    estimated_total_cost_usd: float | None = None


class AgentTrace(BaseModel):
    trace_id: str
    conversation_id: str
    latency_ms: int
    guardrail_status: str
    model: str
    token_usage: TokenUsageTrace = Field(default_factory=TokenUsageTrace)
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    message_count: int


class ChatOptions(BaseModel):
    model: Literal["gpt-5.4", "gpt-4.1", "gpt-5.4-nano"] = "gpt-5.4"
    analysis_depth: Literal["quick", "balanced", "deep"] = "balanced"
    answer_detail: Literal["concise", "balanced", "detailed"] = "balanced"


class ChatRequest(BaseModel):
    query: str
    conversation_id: str
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    options: ChatOptions = Field(default_factory=ChatOptions)


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    final_answer: str
    trace: AgentTrace
    report: ReportSummary | None = None
