import os
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.constants import DEFAULT_RETRIEVAL_TOP_K, MAX_RETRIEVAL_TOP_K
from app.rag.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    embed_query,
    get_embedding_profile,
    to_vector_literal,
)
from app.rag.passage_ids import stable_passage_key
from app.schemas.document import DocumentSearchMatch, DocumentSearchResponse


RetrievalMode = Literal["vector", "keyword", "hybrid"]
HNSW_EF_SEARCH = int(os.getenv("RAG_HNSW_EF_SEARCH", "64"))
FORCE_HNSW_INDEX = os.getenv("RAG_FORCE_HNSW_INDEX", "false").lower() in {
    "1",
    "true",
    "yes",
}
HYBRID_RRF_K = int(os.getenv("RAG_HYBRID_RRF_K", "60"))
HYBRID_VECTOR_WEIGHT = float(os.getenv("RAG_HYBRID_VECTOR_WEIGHT", "2.0"))
HYBRID_KEYWORD_WEIGHT = float(os.getenv("RAG_HYBRID_KEYWORD_WEIGHT", "1.0"))


def _configure_vector_search(db: Session) -> None:
    if FORCE_HNSW_INDEX:
        db.execute(text("SET LOCAL enable_seqscan = off"))
    db.execute(text(f"SET LOCAL hnsw.ef_search = {max(1, HNSW_EF_SEARCH)}"))


def _ensure_embeddings_available(db: Session, model: str, column: str) -> None:
    coverage = (
        db.execute(
            text(f"SELECT COUNT(*) AS total, COUNT({column}) AS indexed " f"FROM document_chunks")
        )
        .mappings()
        .one()
    )
    total = int(coverage["total"])
    indexed = int(coverage["indexed"])
    if total == 0 or indexed != total:
        raise ValueError(
            f"Embedding coverage for {model} is {indexed}/{total} chunks. Run "
            f"'python -m app.scripts.reindex_embeddings --model {model}'."
        )


def _match(row: dict, **ranking: float | int | None) -> DocumentSearchMatch:
    return DocumentSearchMatch(
        passage_key=stable_passage_key(
            source_path=row["source_path"],
            title=row["title"],
            version=row["version"],
            content=row["content"],
        ),
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
        **ranking,
    )


def _vector_search(
    db: Session,
    query: str,
    top_k: int,
    embedding_model: str,
    use_embedding_cache: bool,
    query_embedding: list[float] | None = None,
) -> list[DocumentSearchMatch]:
    profile = get_embedding_profile(embedding_model)
    column = profile.database_column
    _ensure_embeddings_available(db, profile.model, column)
    query_embedding = to_vector_literal(
        query_embedding
        or embed_query(query, profile.model, use_cache=use_embedding_cache)
    )
    _configure_vector_search(db)
    rows = db.execute(
        text(
            f"""
            SELECT
                d.document_id, c.chunk_id, d.title, c.content,
                1 - (c.{column} <=> CAST(:embedding AS vector)) AS score,
                d.source_type, d.source_path, d.department, d.version,
                c.chunk_index
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            WHERE c.{column} IS NOT NULL
            ORDER BY c.{column} <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        ),
        {"embedding": query_embedding, "top_k": top_k},
    ).mappings()
    return [
        _match(
            row,
            vector_score=float(row["score"] or 0),
            vector_rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]


def _keyword_search(db: Session, query: str, top_k: int) -> list[DocumentSearchMatch]:
    rows = db.execute(
        text(
            """
            WITH query_terms AS (
                SELECT to_tsquery(
                    'english',
                    COALESCE(
                        NULLIF(
                            array_to_string(
                                tsvector_to_array(
                                    to_tsvector('english', :query)
                                ),
                                ' | '
                            ),
                            ''
                        ),
                        '__no_match__'
                    )
                ) AS query
            )
            SELECT
                d.document_id, c.chunk_id, d.title, c.content,
                ts_rank_cd(
                    setweight(to_tsvector('english', COALESCE(d.title, '')), 'A') ||
                    setweight(to_tsvector('english', c.content), 'B'),
                    query_terms.query
                ) AS score,
                d.source_type, d.source_path, d.department, d.version,
                c.chunk_index
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            CROSS JOIN query_terms
            WHERE (
                setweight(to_tsvector('english', COALESCE(d.title, '')), 'A') ||
                setweight(to_tsvector('english', c.content), 'B')
            ) @@ query_terms.query
            ORDER BY score DESC, d.title, c.chunk_index
            LIMIT :top_k
            """
        ),
        {"query": query, "top_k": top_k},
    ).mappings()
    return [
        _match(
            row,
            keyword_score=float(row["score"] or 0),
            keyword_rank=rank,
        )
        for rank, row in enumerate(rows, start=1)
    ]


def _hybrid_search(
    db: Session,
    query: str,
    top_k: int,
    embedding_model: str,
    use_embedding_cache: bool,
    query_embedding: list[float] | None = None,
) -> list[DocumentSearchMatch]:
    profile = get_embedding_profile(embedding_model)
    column = profile.database_column
    _ensure_embeddings_available(db, profile.model, column)
    query_embedding = to_vector_literal(
        query_embedding
        or embed_query(query, profile.model, use_cache=use_embedding_cache)
    )
    candidate_k = min(max(top_k * 4, 20), 50)
    _configure_vector_search(db)
    rows = db.execute(
        text(
            f"""
            WITH query_terms AS (
                SELECT to_tsquery(
                    'english',
                    COALESCE(
                        NULLIF(
                            array_to_string(
                                tsvector_to_array(
                                    to_tsvector('english', :query)
                                ),
                                ' | '
                            ),
                            ''
                        ),
                        '__no_match__'
                    )
                ) AS query
            ),
            vector_candidates AS (
                SELECT
                    c.chunk_id,
                    ROW_NUMBER() OVER (
                        ORDER BY c.{column} <=> CAST(:embedding AS vector)
                    ) AS vector_rank,
                    1 - (c.{column} <=> CAST(:embedding AS vector)) AS vector_score
                FROM document_chunks c
                WHERE c.{column} IS NOT NULL
                ORDER BY c.{column} <=> CAST(:embedding AS vector)
                LIMIT :candidate_k
            ),
            keyword_candidates AS (
                SELECT
                    c.chunk_id,
                    ROW_NUMBER() OVER (
                        ORDER BY ts_rank_cd(
                            setweight(to_tsvector('english', COALESCE(d.title, '')), 'A') ||
                            setweight(to_tsvector('english', c.content), 'B'),
                            query_terms.query
                        ) DESC
                    ) AS keyword_rank,
                    ts_rank_cd(
                        setweight(to_tsvector('english', COALESCE(d.title, '')), 'A') ||
                        setweight(to_tsvector('english', c.content), 'B'),
                        query_terms.query
                    ) AS keyword_score
                FROM document_chunks c
                JOIN documents d ON d.document_id = c.document_id
                CROSS JOIN query_terms
                WHERE (
                    setweight(to_tsvector('english', COALESCE(d.title, '')), 'A') ||
                    setweight(to_tsvector('english', c.content), 'B')
                ) @@ query_terms.query
                ORDER BY keyword_score DESC, d.title, c.chunk_index
                LIMIT :candidate_k
            ),
            fused AS (
                SELECT
                    COALESCE(v.chunk_id, k.chunk_id) AS chunk_id,
                    v.vector_rank,
                    k.keyword_rank,
                    v.vector_score,
                    k.keyword_score,
                    :vector_weight *
                        COALESCE(1.0 / (:rrf_k + v.vector_rank), 0) +
                    :keyword_weight *
                        COALESCE(1.0 / (:rrf_k + k.keyword_rank), 0) AS score
                FROM vector_candidates v
                FULL OUTER JOIN keyword_candidates k ON k.chunk_id = v.chunk_id
            )
            SELECT
                d.document_id, c.chunk_id, d.title, c.content, fused.score,
                fused.vector_score, fused.keyword_score,
                fused.vector_rank, fused.keyword_rank,
                d.source_type, d.source_path, d.department, d.version,
                c.chunk_index
            FROM fused
            JOIN document_chunks c ON c.chunk_id = fused.chunk_id
            JOIN documents d ON d.document_id = c.document_id
            ORDER BY fused.score DESC, c.chunk_id
            LIMIT :top_k
            """
        ),
        {
            "query": query,
            "embedding": query_embedding,
            "candidate_k": candidate_k,
            "rrf_k": max(1, HYBRID_RRF_K),
            "vector_weight": max(0, HYBRID_VECTOR_WEIGHT),
            "keyword_weight": max(0, HYBRID_KEYWORD_WEIGHT),
            "top_k": top_k,
        },
    ).mappings()
    return [
        _match(
            row,
            vector_score=(float(row["vector_score"]) if row["vector_score"] is not None else None),
            keyword_score=(
                float(row["keyword_score"]) if row["keyword_score"] is not None else None
            ),
            vector_rank=(int(row["vector_rank"]) if row["vector_rank"] is not None else None),
            keyword_rank=(int(row["keyword_rank"]) if row["keyword_rank"] is not None else None),
        )
        for row in rows
    ]


def search_company_docs(
    *,
    db: Session,
    query: str,
    top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    retrieval_mode: RetrievalMode = "hybrid",
    embedding_model: str | None = None,
    use_embedding_cache: bool = True,
    query_embedding: list[float] | None = None,
) -> DocumentSearchResponse:
    if not query.strip():
        raise ValueError("query must be non-empty")
    if retrieval_mode not in {"vector", "keyword", "hybrid"}:
        raise ValueError(f"unsupported retrieval mode: {retrieval_mode}")

    safe_top_k = max(
        1,
        min(int(top_k or DEFAULT_RETRIEVAL_TOP_K), MAX_RETRIEVAL_TOP_K),
    )
    selected_model = get_embedding_profile(embedding_model or DEFAULT_EMBEDDING_MODEL).model
    if query_embedding is not None:
        expected_dimensions = get_embedding_profile(selected_model).dimensions
        if len(query_embedding) != expected_dimensions:
            raise ValueError(
                f"query_embedding has {len(query_embedding)} dimensions; "
                f"expected {expected_dimensions}."
            )
    if retrieval_mode == "keyword":
        matches = _keyword_search(db, query, safe_top_k)
    elif retrieval_mode == "hybrid":
        matches = _hybrid_search(
            db,
            query,
            safe_top_k,
            selected_model,
            use_embedding_cache,
            query_embedding,
        )
    else:
        matches = _vector_search(
            db,
            query,
            safe_top_k,
            selected_model,
            use_embedding_cache,
            query_embedding,
        )
    return DocumentSearchResponse(
        query=query,
        retrieval_mode=retrieval_mode,
        embedding_model=selected_model,
        embedding_cache_policy=(
            "not_applicable"
            if retrieval_mode == "keyword"
            else ("enabled" if use_embedding_cache else "bypassed")
        ),
        matches=matches,
    )
