import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.agents.agent import ProductAgent
from app.db.models import ConversationMessage
from app.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_conversations import build_agent_messages, get_or_create_conversation
from app.services.chat_trace import build_trace, extract_report_from_response

router = APIRouter(tags=["chat"])
agent = ProductAgent()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    print("Received chat request:", req.query)
    started = time.perf_counter()
    trace_id = str(uuid.uuid4())
    conversation = get_or_create_conversation(db, req.conversation_id, req.query)
    conversation_id = str(conversation.conversation_id)
    config = {"configurable": {"thread_id": conversation_id}}
    if agent.has_checkpoint(conversation_id):
        agent_messages = [HumanMessage(content=req.query)]
    else:
        agent_messages = build_agent_messages(conversation, req.query)

    response = agent.agent.invoke({"messages": agent_messages}, config=config)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = build_trace(
        response=response,
        conversation_id=conversation_id,
        latency_ms=latency_ms,
        trace_id=trace_id,
    )

    answer = response["messages"][-1].content
    if "INVALID_QUERY" in answer:
        answer = "Sorry, I can't assist with that request."

    report = extract_report_from_response(response)

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
