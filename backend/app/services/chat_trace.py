import json
import os

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.reports.links import with_report_urls
from app.schemas.chat import AgentTrace, TokenUsageTrace, ToolArtifact, ToolCallTrace
from app.schemas.report import ReportSummary


def preview(value: object, limit: int = 500) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}..."


def full_result(value: object) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        return str(value)


def as_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def cost_per_1m(env_name: str) -> float | None:
    raw = os.getenv(env_name)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def extract_message_token_usage(message: AIMessage) -> TokenUsageTrace:
    usage = getattr(message, "usage_metadata", None) or {}
    response_metadata = getattr(message, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}

    input_tokens = as_int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or token_usage.get("prompt_tokens")
    )
    output_tokens = as_int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or token_usage.get("completion_tokens")
    )
    total_tokens = as_int(usage.get("total_tokens") or token_usage.get("total_tokens"))

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return TokenUsageTrace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def add_cost_estimate(usage: TokenUsageTrace) -> TokenUsageTrace:
    input_cost_per_1m = cost_per_1m("TRACE_INPUT_COST_PER_1M_TOKENS")
    output_cost_per_1m = cost_per_1m("TRACE_OUTPUT_COST_PER_1M_TOKENS")

    if input_cost_per_1m is None or output_cost_per_1m is None:
        return usage

    input_cost = usage.input_tokens * input_cost_per_1m / 1_000_000
    output_cost = usage.output_tokens * output_cost_per_1m / 1_000_000
    usage.estimated_input_cost_usd = round(input_cost, 8)
    usage.estimated_output_cost_usd = round(output_cost, 8)
    usage.estimated_total_cost_usd = round(input_cost + output_cost, 8)
    return usage


def latest_turn_messages(response: dict) -> list:
    messages = response.get("messages", [])
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], HumanMessage):
            return messages[index:]
    return messages


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


def build_trace(
    *,
    response: dict,
    conversation_id: str,
    latency_ms: int,
    trace_id: str,
    model: str,
) -> AgentTrace:
    messages = latest_turn_messages(response)
    guardrail_status = "UNKNOWN"
    tool_calls: list[ToolCallTrace] = []
    pending_tools: dict[str, ToolCallTrace] = {}
    token_usage = TokenUsageTrace()

    for message in messages:
        content = getattr(message, "content", "")
        if isinstance(message, AIMessage) and content in {"VALID_QUERY", "INVALID_QUERY"}:
            guardrail_status = content
        if isinstance(message, AIMessage):
            message_usage = extract_message_token_usage(message)
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
                matching_trace.result = full_result(message.content)
                matching_trace.result_preview = preview(message.content)
                attach_tool_artifacts(matching_trace, message.content)

    tools_used = list(dict.fromkeys(call.name for call in tool_calls))
    token_usage = add_cost_estimate(token_usage)
    return AgentTrace(
        trace_id=trace_id,
        conversation_id=conversation_id,
        latency_ms=latency_ms,
        guardrail_status=guardrail_status,
        model=model,
        token_usage=token_usage,
        tools_used=tools_used,
        tool_calls=tool_calls,
        message_count=len(messages),
    )


def extract_report_from_response(response: dict) -> ReportSummary | None:
    messages = latest_turn_messages(response)

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

        return with_report_urls(report)

    return None
