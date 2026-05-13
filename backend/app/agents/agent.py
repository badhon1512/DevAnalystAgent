from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from datetime import datetime
from langchain.tools import tool
from app.agents.guardrails import is_valid_query
from app.agents.state import State

checkpointer = InMemorySaver()  
thread = {"configurable": {"thread_id": "5"}}


from app.tools.db import get_db_info_tool, get_sql_database_toolkit_tools, run_readonly_sql_tool
from app.tools.file_system import get_file_management_toolkit
from app.tools.python_sandbox import execute_python_code_tool
from app.tools.rag import search_company_docs_tool
from app.tools.read_write import save_chart_tool
from app.tools.reporting import generate_report_tool


base_llm = ChatOpenAI(model="gpt-5.4-nano")
@tool
def datetime_now() -> str:
    """Get the current date and time in ISO format."""
    return datetime.now().isoformat()

class ProductAgent():

    def __init__(self):
        sql_tools = get_sql_database_toolkit_tools(base_llm)
        self.tools = [
            datetime_now,
            get_db_info_tool,
            *sql_tools,
            run_readonly_sql_tool,
            execute_python_code_tool,
            search_company_docs_tool,
            save_chart_tool,
            generate_report_tool,
            *get_file_management_toolkit(),
        ]
        self.llm = base_llm.bind_tools(self.tools)
        self.finalize_llm = base_llm
        self.agent_graph = StateGraph(State)

        self.agent_graph.add_node("guardrail_check", is_valid_query)
        self.agent_graph.add_node("call_llm", self.call_llm)
        self.agent_graph.add_node("handle_tool_calls", ToolNode(self.tools))

        self.agent_graph.add_edge(START, "guardrail_check")
        self.agent_graph.add_conditional_edges("guardrail_check", self.route_guardrail_check,
                                               {END: END, "call_llm": "call_llm"})
        
        self.agent_graph.add_conditional_edges("call_llm", self.route_tool_calls, 
                                               {END: END, "handle_tool_calls": "handle_tool_calls"} )
        self.agent_graph.add_edge("handle_tool_calls", "call_llm")
        self.agent = self.agent_graph.compile(checkpointer=checkpointer)

        #Lets save the graph
        try:
            png_bytes = self.agent.get_graph().draw_mermaid_png()
            with open("agent_graph.png", "wb") as f:
                f.write(png_bytes)
        except Exception as e:
            print(f"[WARN] Graph render skipped: {e}")
        #img.save("product_agent_graph.png")
        self.system_message = SystemMessage(content="""
You are ProductAI, an AI assistant for product, inventory, sales, and analytics workflows.

Respond in a professional, concise, engineering-style manner.
If you do not know something, say so clearly. Never invent data, records, schema details, or results.
General rules:
1. Always use the provided tools when the answer depends on database contents, schema information, calculations, or analytics.
2. Never guess database values, table names, or column names.
3. Always inspect the database structure first before querying or analyzing database data.
4. Keep answers grounded only in tool results.
5. If a tool fails or required data is unavailable, explain that briefly and do not fabricate an answer.
6. Never response with simulated data, only give give answer based on database data.
7. Use company document search for policies, SOPs, supplier terms, warehouse procedures, internal FAQs, and other unstructured company knowledge.

Database access policy:
1. The database connection is managed by the system.
2. Never access environment variables.
3. Never request or suggest `os.getenv`, `DATABASE_URL`, `create_engine`, SQLAlchemy sessions, engine creation, or manual database connections.
4. Never import internal application modules such as `models`, `db`, `database`, `app.*`, or other project-local code.
5. Use only the approved database tools or approved helper functions provided by the system.
6. If a safe SQL helper is provided, use that helper only for database access.
7. Only query tables and columns that are confirmed by schema inspection.

Required workflow:
1. First call `get_db_info_tool` to inspect the schema and understand available tables and columns.
2. Use `sql_db_list_tables` and `sql_db_schema` from SQLDatabaseToolkit to confirm table names and columns before querying.
3. Use `sql_db_query_checker` before executing a SQL query.
4. If the request needs data retrieval, calculations, aggregations, rankings, time-series summaries, or comparisons, express them in read-only SQL and call `run_readonly_sql_tool`.
5. Return only results that were actually retrieved or computed from tool outputs.
6. If the request needs a derived calculation, trend analysis, transformation, or visualization that is easier in Python, use `execute_python_code_tool`.
7. If the request asks about company policies, SOPs, supplier rules, warehouse procedures, or internal documentation, use `search_company_docs_tool`.

SQL tool policy:
1. Use SQLDatabaseToolkit only for table listing, schema inspection, and query checking.
2. Never request INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, or other write/DDL operations.
3. Keep queries scoped to tables and columns confirmed by `get_db_info_tool` or `sql_db_schema`.
4. Prefer SQL aggregation over fetching large raw row sets.
5. Always add a small LIMIT when returning raw rows.
6. Never call or request `sql_db_query`; actual query execution must use `run_readonly_sql_tool`.

Tool usage guidance:
1. `datetime_now`: use when the current date or time is needed.
2. `get_db_info_tool`: use first for project-specific schema inspection and row counts.
3. `sql_db_list_tables`: list available SQL tables.
4. `sql_db_schema`: inspect SQL table schemas.
5. `sql_db_query_checker`: validate SQL before execution.
6. `run_readonly_sql_tool`: execute checked read-only SQL.
7. `execute_python_code_tool`: use for Python-based analysis, transformations, and chart generation after you have the needed data.
8. `search_company_docs_tool`: search indexed company policies, SOPs, supplier terms, warehouse playbooks, and internal documentation.
9. `save_chart_tool`: use only if you explicitly need to save a base64 PNG chart produced outside the Python sandbox.
10. `generate_report_tool`: use only if the user explicitly asks for a report, export, downloadable summary, or saved document.

RAG workflow:
1. Use SQL tools for live structured facts about products, inventory, sales, returns, and warehouses.
2. Use `search_company_docs_tool` for company policies, SOPs, supplier rules, warehouse procedures, return policies, and internal knowledge.
3. If a question needs both business data and policy context, use both SQL and document search.
4. Cite document titles or source paths when using retrieved company documents.
5. Never invent policy details that were not present in retrieved document chunks.

Report workflow:
1. First complete the grounded analysis using the database tools.
2. Then write the final grounded answer.
3. If and only if the user asked for a report or downloadable artifact, call `generate_report_tool`.
4. Pass your final grounded answer into `generate_report_tool` as the `answer` argument.
5. Build `tool_calls_json` as a JSON array string that summarizes the most relevant tool evidence you used.
6. Call `generate_report_tool` at most once per user request.
7. After the tool succeeds, briefly tell the user that the report was generated and do not call any more tools.

Python analytics workflow:
1. Use SQL tools first to inspect schema and retrieve the minimum relevant data.
2. Use `execute_python_code_tool` when you need derived metrics, comparisons, or graphs.
3. Put the final structured Python output in a variable named `result`.
4. If you generate a matplotlib figure, leave the final figure active so the sandbox can save it automatically.
5. Summarize any returned `charts` artifacts in your final answer when relevant.
6. For charts, prefer professional business visuals: clear title, labeled axes, readable legend, restrained colors, tidy layout, sensible figure size, and sorted categories/time axes where appropriate.
7. Avoid cluttered defaults; choose the chart type that best supports comparison, trend, or ranking.
                                            """)
        
    def route_guardrail_check(self, state: State):
        # Route based on guardrail check result

        last_message = state['messages'][-1]
        #print("Guardrail check result for message:", last_message)
        if "INVALID_QUERY" in last_message.content:
            print("Query is invalid, ending conversation.")
            #return END
            return "call_llm"
        else:
            return "call_llm"
        

    def route_tool_calls(self, state: State):
        # Route tool calls to the appropriate handlers

        last_message = state['messages'][-1]
        #print("Routing tool calls for message:", last_message)
        tool_calls = last_message.tool_calls or []
        if len(tool_calls) > 0:
            return "handle_tool_calls"
        else:
            print("No tool calls found, ending conversation.")
            return END
        
    
    def call_llm(self, state: State) -> State:
        #print("Calling LLM with messages:", state["messages"])
        messages = [self.system_message] + state["messages"]

        last_message = state["messages"][-1]
        if isinstance(last_message, ToolMessage) and getattr(last_message, "name", "") == "generate_report_tool":
            finalize_message = SystemMessage(
                content=(
                    "A report has already been generated for this request. "
                    "Reply to the user with a short confirmation and do not call any more tools."
                )
            )
            llm_response = self.finalize_llm.invoke([self.system_message, finalize_message] + state["messages"])
        else:
            llm_response = self.llm.invoke(messages)
        #print("LLM response:", llm_response)
        return {"messages": [llm_response]}

    def has_checkpoint(self, thread_id: str) -> bool:
        config = {"configurable": {"thread_id": thread_id}}
        return checkpointer.get_tuple(config) is not None




# def invoke_agent(messages: list[dict]) -> dict:
#     return agent.invoke({"messages": messages}, config=thread)
# res = agent.invoke({"messages": "Hi there!"})
# print("Agent invocation complete.", res['messages'][-1].content)
