import uuid

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from app.db.models import ChatUser, Conversation


def get_or_create_conversation(
    db: Session,
    user: ChatUser,
    conversation_id: str | None,
    first_query: str,
) -> Conversation:
    conversation = None
    if conversation_id:
        try:
            conversation = db.get(Conversation, uuid.UUID(conversation_id))
        except ValueError:
            conversation = None

    if conversation and conversation.is_active and conversation.user_id == user.user_id:
        return conversation

    title = first_query.strip()[:48] or "New chat"
    conversation = Conversation(title=title, user_id=user.user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def build_agent_messages(conversation: Conversation, latest_query: str) -> list:
    messages: list = []

    for stored_message in conversation.messages:
        if stored_message.role == "user":
            messages.append(HumanMessage(content=stored_message.content))
        elif stored_message.role == "assistant":
            messages.append(AIMessage(content=stored_message.content))

    messages.append(HumanMessage(content=latest_query))
    return messages
