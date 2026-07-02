from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.agents.state import State

# Guardrails for ProductAI agent to filter out input queries that are not related to its business goal.
load_dotenv(override=True)

INPUT_GUARDRAIL_SYSTEM_MESSAGE = """
You are the ProductAI guardrail.

Allow normal ProductAI, backend, frontend, database, analytics, report, chart, and policy questions.

Only block:
1. Delete or destructive requests, such as delete, remove, drop, truncate, purge, wipe, reset, or erase data/files.
2. Sensitive important information, such as secrets, API keys, passwords, credentials, private employee/HR data, payroll, personal contact details, government IDs, health data, or private customer data.

Return exactly one label:
- VALID_QUERY: the query is allowed.
- INVALID_QUERY: the query asks for deletion/destruction or sensitive important information.

Do not explain your decision. Do not add punctuation. Return only VALID_QUERY or INVALID_QUERY.
"""

# Previous guardrail model kept for reference:
# from langchain_groq import ChatGroq
# guardrail_llm = ChatGroq(model="llama-3.3-70b-versatile")

guardrail_llm = ChatOpenAI(model="gpt-4.1")


def is_valid_query(state: State) -> State:
    user_query = state["messages"][-1].content
    response = guardrail_llm.invoke(
        [
            SystemMessage(content=INPUT_GUARDRAIL_SYSTEM_MESSAGE),
            HumanMessage(content=f'User query: "{user_query}"'),
        ]
    )
    return {"messages": [response]}
