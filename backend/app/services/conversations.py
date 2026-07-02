from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationMessage
from app.schemas.conversation import ConversationDetail, ConversationMessageRead, ConversationSummary


def message_to_schema(message: ConversationMessage) -> ConversationMessageRead:
    return ConversationMessageRead(
        message_id=str(message.message_id),
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        trace=message.trace,
        report=message.report,
    )


def conversation_summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        conversation_id=str(conversation.conversation_id),
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
    )


def list_conversations(db: Session) -> list[ConversationSummary]:
    conversations = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return [conversation_summary(conversation) for conversation in conversations]


def create_conversation(db: Session, title: str | None = None) -> ConversationSummary:
    conversation = Conversation(title=title or "New chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation_summary(conversation)


def get_conversation(db: Session, conversation_id: UUID) -> ConversationDetail:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return ConversationDetail(
        **conversation_summary(conversation).model_dump(),
        messages=[message_to_schema(message) for message in conversation.messages],
    )


def delete_conversation(db: Session, conversation_id: UUID) -> dict[str, bool]:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(conversation)
    db.commit()
    return {"deleted": True}
