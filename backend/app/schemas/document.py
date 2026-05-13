from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str
    content: str
    source_type: str = "manual"
    source_path: str | None = None
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentFileIngestRequest(BaseModel):
    path: str
    title: str | None = None
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentFolderIngestRequest(BaseModel):
    folder: str | None = None
    recursive: bool = False
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSummary(BaseModel):
    document_id: str
    title: str
    source_type: str
    source_path: str | None = None
    department: str | None = None
    version: str | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentFolderIngestResponse(BaseModel):
    documents: list[DocumentSummary] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class DocumentSearchMatch(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    content: str
    score: float
    source_type: str
    source_path: str | None = None
    department: str | None = None
    version: str | None = None
    chunk_index: int


class DocumentSearchResponse(BaseModel):
    query: str
    matches: list[DocumentSearchMatch] = Field(default_factory=list)
