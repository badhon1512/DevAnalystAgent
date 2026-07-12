from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI

from app.tools.db import get_db_info_tool, get_sql_database_toolkit_tools, run_readonly_sql_tool
from app.tools.mcp_tools import get_weather_forecast


MAX_RESEARCH_STEPS = 14
MAX_TOOL_RESULT_CHARS = 12000

base_llm = ChatOpenAI(model="gpt-5.4")


@tool
def datetime_now_for_research() -> str:
    """Return the current date and time in ISO format for seasonality analysis."""
    return datetime.now().isoformat()


def _tool_result_to_content(result: Any) -> str:
    try:
        content = json.dumps(result, default=str)
    except TypeError:
        content = str(result)

    if len(content) > MAX_TOOL_RESULT_CHARS:
        return content[:MAX_TOOL_RESULT_CHARS] + "\n...[truncated]"
    return content


def _tool_map(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {tool_item.name: tool_item for tool_item in tools}


def _research_tools() -> list[BaseTool]:
    sql_checker_tools = [
        sql_tool
        for sql_tool in get_sql_database_toolkit_tools(base_llm)
        if sql_tool.name == "sql_db_query_checker"
    ]
    return [
        datetime_now_for_research,
        get_weather_forecast,
        get_db_info_tool,
        *sql_checker_tools,
        run_readonly_sql_tool,
    ]


def _invoke_tool(tool_item: BaseTool, args: dict[str, Any]) -> Any:
    try:
        return tool_item.invoke(args)
    except Exception as exc:
        return {"error": str(exc), "tool": tool_item.name}


@tool
def researcher_agent(
    question: str,
    focus: str = "product demand, market signals, weather or seasonal impact, inventory risk",
) -> str:
    """
    Run a bounded research sub-agent over structured commerce data.

    Use this when the user asks for deeper market/product-demand research, seasonal or weather-related
    demand analysis, competitor price checks, category opportunities, branch stock risks, or a concise
    research brief grounded in database evidence.
    """
    if not isinstance(question, str) or not question.strip():
        return "Research question must be a non-empty string."

    tools = _research_tools()
    tools_by_name = _tool_map(tools)
    llm = base_llm.bind_tools(tools)

    system_message = SystemMessage(
        content=(
            "You are a focused research sub-agent for StoreWise AI. "
            "You research product demand, seasonality, weather-aware signals, competitor pricing, "
            "branch inventory exposure, returns, and sales trends using only provided tools.\n\n"
            "Rules:\n"
            "1. Always inspect schema with get_db_info_tool before writing SQL.\n"
            "2. Use sql_db_query_checker before every SQL execution.\n"
            "3. Execute data retrieval only through run_readonly_sql_tool.\n"
            "4. Use SELECT/WITH only; never request write operations.\n"
            "5. Prefer aggregated evidence over large raw row lists.\n"
            "6. Ground every conclusion in tool results. If data is missing, say what is missing.\n"
            "7. Return a concise brief with evidence, interpretation, and recommended next actions.\n"
            "8. Use get_weather_forecast when a location, city, branch, weather event, or forecast-sensitive product is relevant.\n\n"
            "StoreWise schema guidance:\n"
            "- Branches are stored in `warehouses`; use `warehouses.code`, `name`, `city`, `postal_code`, `region`, and `country`.\n"
            "- Sales history is stored in `sales`; there is no `orders` table unless schema inspection explicitly shows one.\n"
            "- Product facts are in `products`, `product_variants`, `product_specs`, `product_reviews`, `product_images`.\n"
            "- Inventory risk is in `inventory`, joined to `warehouses`, `products`, and optionally `product_variants`.\n"
            "- Weather/season demand evidence is in `market_signals` and live forecast from `get_weather_forecast`.\n"
            "- Never invent table names. If a table is absent, choose the closest confirmed table from schema inspection."
        )
    )
    user_message = HumanMessage(
        content=(
            f"Research question: {question}\n"
            f"Focus: {focus}\n\n"
            "Produce a concise research brief. Include concrete SQL-derived evidence where available."
        )
    )

    messages: list[BaseMessage] = [system_message, user_message]

    for _ in range(MAX_RESEARCH_STEPS):
        response = llm.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            return str(response.content)

        for tool_call in tool_calls:
            name = tool_call.get("name")
            args = tool_call.get("args") or {}
            tool_item = tools_by_name.get(name)
            if tool_item is None:
                result = {"error": f"Unknown tool requested: {name}"}
            else:
                result = _invoke_tool(tool_item, args)

            messages.append(
                ToolMessage(
                    content=_tool_result_to_content(result),
                    tool_call_id=tool_call.get("id", name or "unknown_tool"),
                    name=name,
                )
            )

    final_prompt = HumanMessage(
        content=(
            "The research tool budget is now exhausted. Based on the evidence already collected, "
            "write the best concise research brief possible. Do not say the user asked you to stop. "
            "If evidence is incomplete, say exactly which evidence was unavailable."
        )
    )
    final_response: AIMessage = base_llm.invoke(messages + [final_prompt])
    return str(final_response.content)
