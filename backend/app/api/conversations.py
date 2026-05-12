from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationMessage
from app.deps import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationMessageRead,
    ConversationSummary,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _message_to_schema(message: ConversationMessage) -> ConversationMessageRead:
    return ConversationMessageRead(
        message_id=str(message.message_id),
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        trace=message.trace,
        report=message.report,
    )


def _summary(conversation: Conversation) -> ConversationSummary:
    return ConversationSummary(
        conversation_id=str(conversation.conversation_id),
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(db: Session = Depends(get_db)):
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [_summary(conversation) for conversation in conversations]


@router.post("", response_model=ConversationSummary)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    conversation = Conversation(title=payload.title or "New chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return _summary(conversation)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return ConversationDetail(
        **_summary(conversation).model_dump(),
        messages=[_message_to_schema(message) for message in conversation.messages],
    )


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(conversation)
    db.commit()
    return {"deleted": True}
