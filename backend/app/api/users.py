from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.users import ChatUserCreate, ChatUserRead
from app.services.users import get_or_create_user, user_to_schema

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/resolve", response_model=ChatUserRead)
def resolve_user(payload: ChatUserCreate, db: Session = Depends(get_db)):
    return user_to_schema(get_or_create_user(db, payload.username))
