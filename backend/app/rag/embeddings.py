import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
BAAI_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


@dataclass(frozen=True)
class EmbeddingProfile:
    model: str
    provider: str
    dimensions: int
    database_column: str


EMBEDDING_PROFILES = {
    OPENAI_EMBEDDING_MODEL: EmbeddingProfile(
        model=OPENAI_EMBEDDING_MODEL,
        provider="openai",
        dimensions=384,
        database_column="embedding",
    ),
    BAAI_EMBEDDING_MODEL: EmbeddingProfile(
        model=BAAI_EMBEDDING_MODEL,
        provider="baai",
        dimensions=384,
        database_column="embedding_baai",
    ),
}

DEFAULT_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    BAAI_EMBEDDING_MODEL,
)
# Backwards-compatible names for existing imports.
EMBEDDING_MODEL = DEFAULT_EMBEDDING_MODEL
EMBEDDING_DIMENSIONS = EMBEDDING_PROFILES[DEFAULT_EMBEDDING_MODEL].dimensions


class EmbeddingsClient(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedClient:
    def __init__(self, model: str):
        from fastembed import TextEmbedding

        cache_dir = os.getenv("FASTEMBED_CACHE_PATH") or None
        self._client = TextEmbedding(model_name=model, cache_dir=cache_dir)

    def embed_query(self, text: str) -> list[float]:
        return list(self._client.query_embed(text))[0].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        batch_size = max(1, int(os.getenv("RAG_EMBEDDING_BATCH_SIZE", "32")))
        return [
            embedding.tolist()
            for embedding in self._client.passage_embed(texts, batch_size=batch_size)
        ]


def get_embedding_profile(model: str | None = None) -> EmbeddingProfile:
    selected = model or DEFAULT_EMBEDDING_MODEL
    try:
        return EMBEDDING_PROFILES[selected]
    except KeyError as exc:
        supported = ", ".join(EMBEDDING_PROFILES)
        raise ValueError(
            f"Unsupported embedding model '{selected}'. Supported models: {supported}"
        ) from exc


def list_embedding_profiles() -> list[EmbeddingProfile]:
    return list(EMBEDDING_PROFILES.values())


@lru_cache(maxsize=len(EMBEDDING_PROFILES))
def get_embeddings_client(model: str | None = None) -> EmbeddingsClient:
    profile = get_embedding_profile(model)
    if profile.provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=profile.model,
            dimensions=profile.dimensions,
            timeout=10,
            max_retries=2,
        )
    return FastEmbedClient(profile.model)


def _validate_dimensions(embedding: list[float], profile: EmbeddingProfile) -> None:
    if len(embedding) != profile.dimensions:
        raise ValueError(
            f"{profile.model} returned {len(embedding)} dimensions; "
            f"expected {profile.dimensions}."
        )


def _embed_query_uncached(text: str, model: str | None = None) -> tuple[float, ...]:
    profile = get_embedding_profile(model)
    embedding = get_embeddings_client(profile.model).embed_query(text)
    _validate_dimensions(embedding, profile)
    return tuple(embedding)


@lru_cache(maxsize=512)
def _embed_query_cached(text: str, model: str | None = None) -> tuple[float, ...]:
    return _embed_query_uncached(text, model)


def embed_query(
    text: str,
    model: str | None = None,
    *,
    use_cache: bool = True,
) -> list[float]:
    embed = _embed_query_cached if use_cache else _embed_query_uncached
    return list(embed(text, model))


def clear_query_embedding_cache() -> None:
    _embed_query_cached.cache_clear()


def embed_documents(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    if not texts:
        return []
    profile = get_embedding_profile(model)
    embeddings = get_embeddings_client(profile.model).embed_documents(texts)
    for embedding in embeddings:
        _validate_dimensions(embedding, profile)
    return embeddings


def to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"
