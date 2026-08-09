from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    embed_documents,
    get_embedding_profile,
)


SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
SUPPORTED_PDF_SUFFIXES = {".pdf"}
SUPPORTED_SUFFIXES = SUPPORTED_TEXT_SUFFIXES | SUPPORTED_PDF_SUFFIXES


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from a PDF, one block per page.

    Scanned PDFs hold images rather than text and yield nothing here. That is
    reported as an error rather than ingested as an empty document, so a silent
    gap never appears in the knowledge base.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(file_path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise ValueError(
            "No extractable text found. The PDF is likely scanned images and needs OCR."
        )
    return text


def read_document_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in SUPPORTED_PDF_SUFFIXES:
        return extract_pdf_text(file_path)
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        return file_path.read_text(encoding="utf-8")
    supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
    raise ValueError(f"Unsupported file type. Supported formats: {supported}")


def ingest_text_document(
    *,
    db: Session,
    title: str,
    content: str,
    source_type: str = "manual",
    source_path: str | None = None,
    department: str | None = None,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
    embedding_models: list[str] | None = None,
) -> Document:
    chunks = chunk_text(content)
    if not chunks:
        raise ValueError("Document content produced no indexable chunks")

    selected_models = embedding_models or [DEFAULT_EMBEDDING_MODEL]
    if len(selected_models) != len(set(selected_models)):
        raise ValueError("embedding_models must not contain duplicates")
    chunk_texts = [chunk.content for chunk in chunks]
    embeddings_by_column = {
        get_embedding_profile(model).database_column: embed_documents(
            chunk_texts,
            model,
        )
        for model in selected_models
    }
    now = datetime.utcnow()
    document = Document(
        title=title,
        source_type=source_type,
        source_path=source_path,
        department=department,
        version=version,
        document_metadata=metadata or {},
        created_at=now,
        updated_at=now,
    )
    db.add(document)
    db.flush()

    for position, chunk in enumerate(chunks):
        embedding_values = {
            column: embeddings[position]
            for column, embeddings in embeddings_by_column.items()
        }
        db.add(
            DocumentChunk(
                document_id=document.document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                **embedding_values,
                chunk_metadata={
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                },
            )
        )

    db.commit()
    db.refresh(document)
    return document


def ingest_text_file(
    *,
    db: Session,
    path: str | Path,
    title: str | None = None,
    department: str | None = None,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
    embedding_models: list[str] | None = None,
) -> Document:
    file_path = Path(path)
    content = read_document_file(file_path)
    return ingest_text_document(
        db=db,
        title=title or file_path.stem.replace("_", " ").replace("-", " ").title(),
        content=content,
        source_type="pdf" if file_path.suffix.lower() in SUPPORTED_PDF_SUFFIXES else "file",
        source_path=str(file_path),
        department=department,
        version=version,
        metadata=metadata,
        embedding_models=embedding_models,
    )
