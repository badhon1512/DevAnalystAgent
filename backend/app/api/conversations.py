from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationSummary
from app.services.conversations import (
    create_conversation as create_conversation_service,
    delete_conversation as delete_conversation_service,
    get_conversation as get_conversation_service,
    list_conversations as list_conversations_service,
)
from app.services.users import get_or_create_user

router = APIRouter(prefix="/conversations", tags=["conversations"])
UsernameQuery = Query(..., min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")


@router.get("", response_model=list[ConversationSummary])
def list_conversations(username: str = UsernameQuery, db: Session = Depends(get_db)):
    user = get_or_create_user(db, username)
    return list_conversations_service(db, user)


@router.post("", response_model=ConversationSummary)
def create_conversation(
    payload: ConversationCreate,
    username: str = UsernameQuery,
    db: Session = Depends(get_db),
):
    user = get_or_create_user(db, username)
    return create_conversation_service(db, user, payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    username: str = UsernameQuery,
    db: Session = Depends(get_db),
):
    user = get_or_create_user(db, username)
    return get_conversation_service(db, user, conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    username: str = UsernameQuery,
    db: Session = Depends(get_db),
):
    user = get_or_create_user(db, username)
    return delete_conversation_service(db, user, conversation_id)
