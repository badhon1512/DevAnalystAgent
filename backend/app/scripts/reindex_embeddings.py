import argparse

from app.db.models import DocumentChunk
from app.db.session import SessionLocal
from app.rag.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_PROFILES,
    embed_documents,
    get_embedding_profile,
)


def reindex_embedding_model(
    model: str,
    *,
    batch_size: int = 32,
    force: bool = False,
) -> int:
    profile = get_embedding_profile(model)
    total = 0
    last_chunk_id = None

    with SessionLocal() as db:
        while True:
            query = db.query(DocumentChunk).order_by(DocumentChunk.chunk_id)
            if last_chunk_id is not None:
                query = query.filter(DocumentChunk.chunk_id > last_chunk_id)
            if not force:
                query = query.filter(
                    getattr(DocumentChunk, profile.database_column).is_(None)
                )
            chunks = query.limit(batch_size).all()
            if not chunks:
                break

            embeddings = embed_documents(
                [chunk.content for chunk in chunks],
                profile.model,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                setattr(chunk, profile.database_column, embedding)
            db.commit()
            total += len(chunks)
            last_chunk_id = chunks[-1].chunk_id
            print(f"Indexed {total} chunks with {profile.model}...")

    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a selected embedding index for existing RAG chunks."
    )
    parser.add_argument(
        "--model",
        choices=list(EMBEDDING_PROFILES),
        default=DEFAULT_EMBEDDING_MODEL,
    )
    parser.add_argument("--all-models", action="store_true")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    models = list(EMBEDDING_PROFILES) if args.all_models else [args.model]
    for model in models:
        count = reindex_embedding_model(
            model,
            batch_size=args.batch_size,
            force=args.force,
        )
        print(f"Completed {model}: {count} chunks updated.")


if __name__ == "__main__":
    main()
