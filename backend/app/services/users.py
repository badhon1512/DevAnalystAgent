from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ChatUser
from app.schemas.users import ChatUserRead


def normalize_username(username: str) -> str:
    return username.strip().lower()


def user_to_schema(user: ChatUser) -> ChatUserRead:
    return ChatUserRead(
        user_id=str(user.user_id),
        username=user.username,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def get_or_create_user(db: Session, username: str) -> ChatUser:
    normalized = normalize_username(username)
    user = db.query(ChatUser).filter(ChatUser.username == normalized).one_or_none()
    if user:
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    user = ChatUser(username=normalized)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
