import os
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document
from app.rag.ingestion import SUPPORTED_TEXT_SUFFIXES, ingest_text_document, ingest_text_file
from app.rag.retriever import search_company_docs
from app.schemas.document import (
    DocumentCreate,
    DocumentFileIngestRequest,
    DocumentFolderIngestRequest,
    DocumentFolderIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSummary,
)

DEFAULT_DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def documents_root() -> Path:
    return Path(os.getenv("RAG_DOCUMENTS_DIR", DEFAULT_DOCUMENTS_DIR)).resolve()


def resolve_under_documents_root(path: str | None = None) -> Path:
    root = documents_root()
    candidate = (root / path).resolve() if path else root

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path must stay inside RAG_DOCUMENTS_DIR.") from exc

    return candidate


def document_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        document_id=str(document.document_id),
        title=document.title,
        source_type=document.source_type,
        source_path=document.source_path,
        department=document.department,
        version=document.version,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def list_documents(db: Session) -> list[DocumentSummary]:
    documents = db.query(Document).order_by(Document.updated_at.desc()).all()
    return [document_summary(document) for document in documents]


def create_document(db: Session, payload: DocumentCreate) -> DocumentSummary:
    try:
        document = ingest_text_document(
            db=db,
            title=payload.title,
            content=payload.content,
            source_type=payload.source_type,
            source_path=payload.source_path,
            department=payload.department,
            version=payload.version,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return document_summary(document)


def create_document_from_file(db: Session, payload: DocumentFileIngestRequest) -> DocumentSummary:
    file_path = resolve_under_documents_root(payload.path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found.")

    try:
        document = ingest_text_file(
            db=db,
            path=file_path,
            title=payload.title,
            department=payload.department,
            version=payload.version,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return document_summary(document)


def create_documents_from_folder(
    db: Session,
    payload: DocumentFolderIngestRequest,
) -> DocumentFolderIngestResponse:
    folder_path = resolve_under_documents_root(payload.folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Document folder not found.")

    pattern = "**/*" if payload.recursive else "*"
    candidates = sorted(
        path
        for path in folder_path.glob(pattern)
        if path.is_file() and path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES
    )

    documents: list[DocumentSummary] = []
    skipped: list[str] = []
    for file_path in candidates:
        try:
            document = ingest_text_file(
                db=db,
                path=file_path,
                department=payload.department,
                version=payload.version,
                metadata=payload.metadata,
            )
        except ValueError as exc:
            skipped.append(f"{file_path.name}: {exc}")
            continue
        documents.append(document_summary(document))

    return DocumentFolderIngestResponse(documents=documents, skipped=skipped)


def search_documents(db: Session, payload: DocumentSearchRequest) -> DocumentSearchResponse:
    try:
        return search_company_docs(db=db, query=payload.query, top_k=payload.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def delete_document(db: Session, document_id: UUID) -> dict[str, bool]:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.delete(document)
    db.commit()
    return {"deleted": True}
