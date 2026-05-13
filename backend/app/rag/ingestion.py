from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_documents


SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}


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
) -> Document:
    chunks = chunk_text(content)
    if not chunks:
        raise ValueError("Document content produced no indexable chunks")

    embeddings = embed_documents([chunk.content for chunk in chunks])
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

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        db.add(
            DocumentChunk(
                document_id=document.document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                embedding=embedding,
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
) -> Document:
    file_path = Path(path)
    if file_path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_TEXT_SUFFIXES))
        raise ValueError(f"Unsupported file type. Supported text formats: {supported}")

    content = file_path.read_text(encoding="utf-8")
    return ingest_text_document(
        db=db,
        title=title or file_path.stem.replace("_", " ").replace("-", " ").title(),
        content=content,
        source_type="file",
        source_path=str(file_path),
        department=department,
        version=version,
        metadata=metadata,
    )
