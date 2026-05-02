from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCallTrace(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_preview: str | None = None


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


class ChatRequest(BaseModel):
    query: str
    conversation_id: str


class ChatResponse(BaseModel):
    answer: str
    final_answer: str
    trace: AgentTrace
