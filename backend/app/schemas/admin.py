from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.conversation import ConversationMessageRead


class AdminLoginRequest(BaseModel):
    secret: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AdminLoginResponse(BaseModel):
    token: str


class AdminConversationSummary(BaseModel):
    conversation_id: str
    username: str | None = None
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: str | None = None


class AdminConversationDetail(AdminConversationSummary):
    messages: list[ConversationMessageRead] = Field(default_factory=list)


class AdminConversationStatusUpdate(BaseModel):
    is_active: bool
