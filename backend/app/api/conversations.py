from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationSummary
from app.services.conversations import (
    create_conversation as create_conversation_service,
    delete_conversation as delete_conversation_service,
    get_conversation as get_conversation_service,
    list_conversations as list_conversations_service,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(db: Session = Depends(get_db)):
    return list_conversations_service(db)


@router.post("", response_model=ConversationSummary)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    return create_conversation_service(db, payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    return get_conversation_service(db, conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    return delete_conversation_service(db, conversation_id)
