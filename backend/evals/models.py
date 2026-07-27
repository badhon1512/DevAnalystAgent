from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
