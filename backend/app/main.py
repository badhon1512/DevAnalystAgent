from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import AIMessage, ToolMessage
from app.agents.agent import ProductAgent
from app.api.products import router as products_router
from app.api.inventories import router as inventories_router
from app.schemas.chat import AgentTrace, ChatRequest, ChatResponse, ToolCallTrace
from app.schemas.chat import TokenUsageTrace
from dotenv import load_dotenv
import os
from pathlib import Path
import time
import uuid

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


app = FastAPI(title="ProductAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(inventories_router)


@app.get("/health")
async def read_root():

    return {"message": "Welcome to the ProductAI Backend!"}


class ComputeRequest(BaseModel):
    x: int
    y: int
@app.post("/compute")
def compute(req: ComputeRequest):
    # call the function end-to-end
    return {"result": req.x + req.y}


agent = ProductAgent()


def _preview(value: object, limit: int = 500) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def _as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _cost_per_1m(env_name: str) -> float | None:
    raw = os.getenv(env_name)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_message_token_usage(message: AIMessage) -> TokenUsageTrace:
    usage = getattr(message, "usage_metadata", None) or {}
    response_metadata = getattr(message, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}

    input_tokens = _as_int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or token_usage.get("prompt_tokens")
    )
    output_tokens = _as_int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or token_usage.get("completion_tokens")
    )
    total_tokens = _as_int(usage.get("total_tokens") or token_usage.get("total_tokens"))

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return TokenUsageTrace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _add_cost_estimate(usage: TokenUsageTrace) -> TokenUsageTrace:
    input_cost_per_1m = _cost_per_1m("TRACE_INPUT_COST_PER_1M_TOKENS")
    output_cost_per_1m = _cost_per_1m("TRACE_OUTPUT_COST_PER_1M_TOKENS")

    if input_cost_per_1m is None or output_cost_per_1m is None:
        return usage

    input_cost = usage.input_tokens * input_cost_per_1m / 1_000_000
    output_cost = usage.output_tokens * output_cost_per_1m / 1_000_000
    usage.estimated_input_cost_usd = round(input_cost, 8)
    usage.estimated_output_cost_usd = round(output_cost, 8)
    usage.estimated_total_cost_usd = round(input_cost + output_cost, 8)
    return usage


def _build_trace(
    *,
    response: dict,
    conversation_id: str,
    latency_ms: int,
    trace_id: str,
) -> AgentTrace:
    messages = response.get("messages", [])
    guardrail_status = "UNKNOWN"
    tool_calls: list[ToolCallTrace] = []
    pending_tools: dict[str, ToolCallTrace] = {}
    token_usage = TokenUsageTrace()

    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(message, AIMessage) and content in {"VALID_QUERY", "INVALID_QUERY"}:
            guardrail_status = content
        if isinstance(message, AIMessage):
            message_usage = _extract_message_token_usage(message)
            token_usage.input_tokens += message_usage.input_tokens
            token_usage.output_tokens += message_usage.output_tokens
            token_usage.total_tokens += message_usage.total_tokens

        for call in getattr(message, "tool_calls", []) or []:
            trace = ToolCallTrace(
                name=call.get("name", "unknown_tool"),
                args=call.get("args") or {},
            )
            tool_calls.append(trace)
            if call.get("id"):
                pending_tools[call["id"]] = trace

        if isinstance(message, ToolMessage):
            matching_trace = pending_tools.get(message.tool_call_id)
            if matching_trace:
                matching_trace.result_preview = _preview(message.content)

    tools_used = list(dict.fromkeys(call.name for call in tool_calls))
    token_usage = _add_cost_estimate(token_usage)
    return AgentTrace(
        trace_id=trace_id,
        conversation_id=conversation_id,
        latency_ms=latency_ms,
        guardrail_status=guardrail_status,
        model="gpt-5.4-nano",
        token_usage=token_usage,
        tools_used=tools_used,
        tool_calls=tool_calls,
        message_count=len(messages),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    print("Received chat request:", req.query)
    started = time.perf_counter()
    trace_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": req.conversation_id or trace_id}}

    response = agent.agent.invoke({"messages": [req.query]}, config=config)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = _build_trace(
        response=response,
        conversation_id=req.conversation_id,
        latency_ms=latency_ms,
        trace_id=trace_id,
    )

    answer = response["messages"][-1].content
    if "INVALID_QUERY" in answer:
        answer = "Sorry, I can't assist with that request."

    return ChatResponse(answer=answer, final_answer=answer, trace=trace)

from sqlalchemy.orm import Session

from app.deps import get_db
from app.db.session import engine
from app.tools.db import get_db_info
from fastapi import Depends, Query


@app.get("/db-info")
def db_info(
    db: Session = Depends(get_db),
    include_row_counts: bool = Query(default=True),
):
    return get_db_info(db=db, engine=engine, include_row_counts=include_row_counts).model_dump()
