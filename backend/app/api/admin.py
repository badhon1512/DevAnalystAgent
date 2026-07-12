import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Conversation
from app.deps import get_db
from app.schemas.admin import (
    AdminConversationDetail,
    AdminConversationStatusUpdate,
    AdminConversationSummary,
    AdminLoginRequest,
    AdminLoginResponse,
)
from app.services.conversations import message_to_schema

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_secret() -> str:
    return os.getenv("ADMIN_SECRET", "dev-admin-secret")


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "admin")


def require_admin(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required.")

    token = authorization.removeprefix("Bearer ").strip()
    if token != _admin_secret():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token.")


def _last_message_preview(conversation: Conversation) -> str | None:
    if not conversation.messages:
        return None
    content = conversation.messages[-1].content.strip()
    return content[:160] if content else None


def _summary(conversation: Conversation) -> AdminConversationSummary:
    return AdminConversationSummary(
        conversation_id=str(conversation.conversation_id),
        username=conversation.user.username if conversation.user else None,
        title=conversation.title,
        is_active=conversation.is_active,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
        last_message_preview=_last_message_preview(conversation),
    )


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest):
    if payload.secret != _admin_secret() or payload.password != _admin_password():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials.")
    return AdminLoginResponse(token=_admin_secret())


@router.get("/conversations", response_model=list[AdminConversationSummary])
def admin_list_conversations(
    include_inactive: bool = True,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Conversation)
    if not include_inactive:
        query = query.filter(Conversation.is_active.is_(True))
    conversations = query.order_by(Conversation.updated_at.desc()).all()
    return [_summary(conversation) for conversation in conversations]


@router.get("/conversations/{conversation_id}", response_model=AdminConversationDetail)
def admin_get_conversation(
    conversation_id: UUID,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return AdminConversationDetail(
        **_summary(conversation).model_dump(),
        messages=[message_to_schema(message) for message in conversation.messages],
    )


@router.patch("/conversations/{conversation_id}", response_model=AdminConversationSummary)
def admin_update_conversation_status(
    conversation_id: UUID,
    payload: AdminConversationStatusUpdate,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conversation.is_active = payload.is_active
    db.commit()
    db.refresh(conversation)
    return _summary(conversation)


@router.delete("/conversations/{conversation_id}")
def admin_delete_conversation(
    conversation_id: UUID,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(conversation)
    db.commit()
    return {"deleted": True}
