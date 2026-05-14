from langchain_core.tools import tool

from app.db.session import SessionLocal
from app.rag.retriever import search_company_docs


@tool
def search_company_docs_tool(query: str, top_k: int = 5) -> dict:
    """
    Search indexed company documents such as policies, SOPs, supplier terms,
    warehouse playbooks, and internal FAQs. Use this for unstructured company
    knowledge, not for live product/inventory/sales database facts.
    """
    with SessionLocal() as db:
        return search_company_docs(db=db, query=query, top_k=top_k).model_dump()
