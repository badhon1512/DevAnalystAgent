from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chat import AgentTrace
from app.schemas.report import ReportSummary


class ConversationMessageRead(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime
    trace: AgentTrace | None = None
    report: ReportSummary | None = None


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    is_active: bool = True
    username: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessageRead] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str | None = None
