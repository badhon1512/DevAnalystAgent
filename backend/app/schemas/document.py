from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.rag.constants import DEFAULT_RETRIEVAL_TOP_K


class DocumentCreate(BaseModel):
    title: str
    content: str
    source_type: str = "manual"
    source_path: str | None = None
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_models: list[str] | None = None


class DocumentFileIngestRequest(BaseModel):
    path: str
    title: str | None = None
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_models: list[str] | None = None


class DocumentFolderIngestRequest(BaseModel):
    folder: str | None = None
    recursive: bool = False
    department: str | None = None
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_models: list[str] | None = None


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
    top_k: int = DEFAULT_RETRIEVAL_TOP_K
    retrieval_mode: Literal["vector", "keyword", "hybrid"] = "hybrid"
    embedding_model: str | None = None
    use_embedding_cache: bool = True


class DocumentSearchMatch(BaseModel):
    document_id: str
    chunk_id: str
    passage_key: str
    title: str
    content: str
    score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    vector_rank: int | None = None
    keyword_rank: int | None = None
    source_type: str
    source_path: str | None = None
    department: str | None = None
    version: str | None = None
    chunk_index: int


class DocumentSearchResponse(BaseModel):
    query: str
    retrieval_mode: Literal["vector", "keyword", "hybrid"] = "hybrid"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_policy: Literal["enabled", "bypassed", "not_applicable"] = "enabled"
    matches: list[DocumentSearchMatch] = Field(default_factory=list)
