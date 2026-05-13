from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.embeddings import embed_query, to_vector_literal
from app.schemas.document import DocumentSearchMatch, DocumentSearchResponse


def search_company_docs(
    *,
    db: Session,
    query: str,
    top_k: int = 5,
) -> DocumentSearchResponse:
    if not query.strip():
        raise ValueError("query must be non-empty")

    safe_top_k = max(1, min(int(top_k or 5), 12))
    query_embedding = to_vector_literal(embed_query(query))
    rows = db.execute(
        text(
            """
            SELECT
                d.document_id,
                c.chunk_id,
                d.title,
                c.content,
                1 - (c.embedding <=> CAST(:embedding AS vector)) AS score,
                d.source_type,
                d.source_path,
                d.department,
                d.version,
                c.chunk_index
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        ),
        {"embedding": query_embedding, "top_k": safe_top_k},
    ).mappings()

    return DocumentSearchResponse(
        query=query,
        matches=[
            DocumentSearchMatch(
                document_id=str(row["document_id"]),
                chunk_id=str(row["chunk_id"]),
                title=row["title"],
                content=row["content"],
                score=float(row["score"] or 0),
                source_type=row["source_type"],
                source_path=row["source_path"],
                department=row["department"],
                version=row["version"],
                chunk_index=row["chunk_index"],
            )
            for row in rows
        ],
    )
