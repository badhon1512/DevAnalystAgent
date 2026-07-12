from datetime import datetime

from pydantic import BaseModel, Field


class ChatUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")


class ChatUserRead(BaseModel):
    user_id: str
    username: str
    created_at: datetime
    updated_at: datetime
