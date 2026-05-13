import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document
from app.deps import get_db
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

router = APIRouter(prefix="/documents", tags=["documents"])

DEFAULT_DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "knowledge"


def _documents_root() -> Path:
    return Path(os.getenv("RAG_DOCUMENTS_DIR", DEFAULT_DOCUMENTS_DIR)).resolve()


def _resolve_under_documents_root(path: str | None = None) -> Path:
    root = _documents_root()
    candidate = (root / path).resolve() if path else root

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path must stay inside RAG_DOCUMENTS_DIR.") from exc

    return candidate


def _summary(document: Document) -> DocumentSummary:
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


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    documents = db.query(Document).order_by(Document.updated_at.desc()).all()
    return [_summary(document) for document in documents]


@router.post("", response_model=DocumentSummary)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
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

    return _summary(document)


@router.post("/from-file", response_model=DocumentSummary)
def create_document_from_file(payload: DocumentFileIngestRequest, db: Session = Depends(get_db)):
    file_path = _resolve_under_documents_root(payload.path)
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

    return _summary(document)


@router.post("/from-folder", response_model=DocumentFolderIngestResponse)
def create_documents_from_folder(
    payload: DocumentFolderIngestRequest,
    db: Session = Depends(get_db),
):
    folder_path = _resolve_under_documents_root(payload.folder)
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
        documents.append(_summary(document))

    return DocumentFolderIngestResponse(documents=documents, skipped=skipped)


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(payload: DocumentSearchRequest, db: Session = Depends(get_db)):
    try:
        return search_company_docs(db=db, query=payload.query, top_k=payload.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{document_id}")
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    db.delete(document)
    db.commit()
    return {"deleted": True}
