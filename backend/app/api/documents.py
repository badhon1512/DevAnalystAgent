from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.document import (
    DocumentCreate,
    DocumentFileIngestRequest,
    DocumentFolderIngestRequest,
    DocumentFolderIngestResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSummary,
)
from app.services.documents import (
    create_document as create_document_service,
    create_document_from_file as create_document_from_file_service,
    create_documents_from_folder as create_documents_from_folder_service,
    delete_document as delete_document_service,
    list_documents as list_documents_service,
    search_documents as search_documents_service,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentSummary])
def list_documents(db: Session = Depends(get_db)):
    return list_documents_service(db)


@router.post("", response_model=DocumentSummary)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    return create_document_service(db, payload)


@router.post("/from-file", response_model=DocumentSummary)
def create_document_from_file(payload: DocumentFileIngestRequest, db: Session = Depends(get_db)):
    return create_document_from_file_service(db, payload)


@router.post("/from-folder", response_model=DocumentFolderIngestResponse)
def create_documents_from_folder(
    payload: DocumentFolderIngestRequest,
    db: Session = Depends(get_db),
):
    return create_documents_from_folder_service(db, payload)


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    payload: DocumentSearchRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return search_documents_service(db, payload)


@router.delete("/{document_id}")
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    return delete_document_service(db, document_id)
