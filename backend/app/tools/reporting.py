import json

from langchain.tools import tool

from app.agents.report_agent import ReportAgent

report_agent = ReportAgent()


@tool
def generate_report_tool(
    question: str,
    answer: str,
    trace_id: str = "",
    tool_calls_json: str = "[]",
) -> str:
    """
    Generate a saved business report artifact after you already have a grounded answer.
    Use this only when the user explicitly asks for a report, downloadable report, summary document,
    or file output. Pass the user's request as `question`, your grounded response as `answer`,
    and a JSON string of the tool evidence you relied on as `tool_calls_json`.
    """
    try:
        tool_calls = json.loads(tool_calls_json) if tool_calls_json else []
    except json.JSONDecodeError:
        tool_calls = []

    report = report_agent.generate(
        question=question,
        answer=answer,
        trace_id=trace_id or None,
        tool_calls=tool_calls,
    )
    return report.model_dump_json()
