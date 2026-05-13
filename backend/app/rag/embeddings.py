import os

from langchain_openai import OpenAIEmbeddings


EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536


def get_embeddings_client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def embed_query(text: str) -> list[float]:
    return get_embeddings_client().embed_query(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return get_embeddings_client().embed_documents(texts)


def to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"
