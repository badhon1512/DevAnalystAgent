import os
import json
from pathlib import Path
from datetime import datetime
import time
import uuid

from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.agent import ProductAgent
from app.api.conversations import router as conversations_router
from app.api.inventories import router as inventories_router
from app.api.products import router as products_router
from app.db.models import Conversation, ConversationMessage
from app.db.session import engine
from app.deps import get_db
from app.reports.storage import load_report, resolve_asset_path
from app.schemas.chat import (
    AgentTrace,
    ChatRequest,
    ChatResponse,
    ToolArtifact,
    TokenUsageTrace,
    ToolCallTrace,
)
from app.schemas.report import GeneratedReport, ReportSummary
from app.tools.db import get_db_info
from app.tools.voice import VoiceTranscriptionUnavailable, transcribe_audio_bytes

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)


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
app.include_router(conversations_router)


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

    def attach_tool_artifacts(trace: ToolCallTrace, content: object) -> None:
        if trace.name != "execute_python_code_tool" or not isinstance(content, str):
            return

        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return

        for chart in payload.get("charts", []) or []:
            filename = chart.get("filename")
            if not filename:
                continue
            trace.artifacts.append(
                ToolArtifact(
                    type="chart",
                    label=chart.get("label") or f"Chart: {filename}",
                    filename=filename,
                    content_type=chart.get("content_type", "image/png"),
                    view_url=f"/charts/view/{filename}",
                    download_url=f"/charts/download/{filename}",
                )
            )

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
                attach_tool_artifacts(matching_trace, message.content)

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


def _with_report_urls(report: ReportSummary | GeneratedReport) -> ReportSummary | GeneratedReport:
    for asset in report.assets:
        asset.view_url = f"/reports/{report.report_id}/assets/{asset.filename}"
        asset.download_url = f"/reports/{report.report_id}/download/{asset.filename}"
    return report


def _extract_report_from_response(response: dict) -> ReportSummary | None:
    messages = response.get("messages", [])

    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        tool_name = getattr(message, "name", "") or ""
        if tool_name != "generate_report_tool":
            continue

        content = getattr(message, "content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        try:
            report = ReportSummary.model_validate_json(content)
        except Exception:
            try:
                report = ReportSummary.model_validate(json.loads(content))
            except Exception:
                continue

        return _with_report_urls(report)

    return None


def _get_or_create_conversation(db: Session, conversation_id: str | None, first_query: str) -> Conversation:
    conversation = None
    if conversation_id:
        try:
            conversation = db.get(Conversation, uuid.UUID(conversation_id))
        except ValueError:
            conversation = None

    if conversation:
        return conversation

    title = first_query.strip()[:48] or "New chat"
    conversation = Conversation(title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _build_agent_messages(conversation: Conversation, latest_query: str) -> list:
    messages: list = []

    for stored_message in conversation.messages:
        if stored_message.role == "user":
            messages.append(HumanMessage(content=stored_message.content))
        elif stored_message.role == "assistant":
            messages.append(AIMessage(content=stored_message.content))

    messages.append(HumanMessage(content=latest_query))
    return messages


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    print("Received chat request:", req.query)
    started = time.perf_counter()
    trace_id = str(uuid.uuid4())
    conversation = _get_or_create_conversation(db, req.conversation_id, req.query)
    conversation_id = str(conversation.conversation_id)
    config = {"configurable": {"thread_id": conversation_id}}
    if agent.has_checkpoint(conversation_id):
        agent_messages = [HumanMessage(content=req.query)]
    else:
        agent_messages = _build_agent_messages(conversation, req.query)

    response = agent.agent.invoke({"messages": agent_messages}, config=config)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = _build_trace(
        response=response,
        conversation_id=conversation_id,
        latency_ms=latency_ms,
        trace_id=trace_id,
    )

    answer = response["messages"][-1].content
    if "INVALID_QUERY" in answer:
        answer = "Sorry, I can't assist with that request."

    report = _extract_report_from_response(response)

    user_message = ConversationMessage(
        conversation_id=conversation.conversation_id,
        role="user",
        content=req.query,
    )
    assistant_message = ConversationMessage(
        conversation_id=conversation.conversation_id,
        role="assistant",
        content=answer,
        trace=trace.model_dump(mode="json"),
        report=report.model_dump(mode="json") if report else None,
    )
    db.add_all([user_message, assistant_message])
    conversation.updated_at = datetime.utcnow()
    if conversation.title == "New chat":
        conversation.title = req.query.strip()[:48] or "New chat"
    db.commit()

    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        final_answer=answer,
        trace=trace,
        report=report,
    )


@app.get("/db-info")
def db_info(
    db: Session = Depends(get_db),
    include_row_counts: bool = Query(default=True),
):
    return get_db_info(db=db, engine=engine, include_row_counts=include_row_counts).model_dump()


@app.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Upload an audio file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    suffix = Path(file.filename or "recording.webm").suffix or ".webm"
    try:
        return transcribe_audio_bytes(content, suffix=suffix).model_dump()
    except VoiceTranscriptionUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@app.get("/reports/{report_id}", response_model=GeneratedReport)
def get_report(report_id: str):
    try:
        report = load_report(report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report not found.") from exc
    return _with_report_urls(report)


@app.get("/reports/{report_id}/assets/{filename}")
def view_report_asset(report_id: str, filename: str):
    try:
        asset_path = resolve_asset_path(report_id, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report asset not found.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Report asset not found.")

    media_type = "text/plain"
    if asset_path.suffix == ".md":
        media_type = "text/markdown; charset=utf-8"
    elif asset_path.suffix == ".html":
        media_type = "text/html; charset=utf-8"
    elif asset_path.suffix == ".json":
        media_type = "application/json"
    elif asset_path.suffix == ".pdf":
        media_type = "application/pdf"
    elif asset_path.suffix == ".png":
        media_type = "image/png"

    return FileResponse(asset_path, media_type=media_type)


@app.get("/reports/{report_id}/download/{filename}")
def download_report_asset(report_id: str, filename: str):
    try:
        asset_path = resolve_asset_path(report_id, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report asset not found.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Report asset not found.")

    return FileResponse(asset_path, filename=asset_path.name)


@app.get("/charts/view/{filename}")
def view_chart(filename: str):
    charts_dir = Path("sandbox_charts").resolve()
    asset_path = (charts_dir / filename).resolve()

    try:
        asset_path.relative_to(charts_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid chart path.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found.")

    return FileResponse(asset_path, media_type="image/png")


@app.get("/charts/download/{filename}")
def download_chart(filename: str):
    charts_dir = Path("sandbox_charts").resolve()
    asset_path = (charts_dir / filename).resolve()

    try:
        asset_path.relative_to(charts_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid chart path.") from exc

    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found.")

    return FileResponse(asset_path, media_type="image/png", filename=asset_path.name)
