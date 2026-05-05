from langchain_groq import ChatGroq
from app.agents.state import State
from dotenv import load_dotenv
#Guardrails for ProductAI agent to filter out input queries that are not related to product or inventory management.
load_dotenv(override=True)

INPUT_GUARDRAIL_SYSTEM_MESSAGE = """
You are a guardrail system that ensures user queries are relevant to product and inventory management.
You should allow all database relaetd queries
If a query is not relevant, respond with "INVALID_QUERY".
"""

groq_llm = ChatGroq(model="llama-3.3-70b-versatile")

def is_valid_query(state: State) -> State:
    prompt = f"""
    {INPUT_GUARDRAIL_SYSTEM_MESSAGE}

    User Query: "{state['messages'][-1].content}"
    Is this query relevant to product or inventory management? Answer "VALID_QUERY" or "INVALID_QUERY".
    But You should allow greatings and polite conversation.
    """

    response = groq_llm.invoke(prompt)
    return {"messages": [response]}