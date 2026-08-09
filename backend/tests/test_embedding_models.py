from app.rag import embeddings
from app.rag.constants import DEFAULT_RETRIEVAL_TOP_K
from app.schemas.document import DocumentSearchRequest


class FakeEmbeddingsClient:
    def __init__(self, dimensions: int):
        self.dimensions = dimensions

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))] * self.dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] * self.dimensions for text in texts]


def test_baai_is_the_default_embedding_profile() -> None:
    profile = embeddings.get_embedding_profile()

    assert profile.model == "BAAI/bge-small-en-v1.5"
    assert profile.provider == "baai"
    assert profile.dimensions == 384
    assert profile.database_column == "embedding_baai"


def test_openai_profile_remains_available_for_comparison() -> None:
    profile = embeddings.get_embedding_profile("text-embedding-3-small")

    assert profile.provider == "openai"
    assert profile.dimensions == 384
    assert profile.database_column == "embedding"


def test_openai_client_requests_profile_dimensions(monkeypatch) -> None:
    captured = {}

    class FakeOpenAIEmbeddings:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "langchain_openai.OpenAIEmbeddings",
        FakeOpenAIEmbeddings,
    )
    embeddings.get_embeddings_client.cache_clear()

    embeddings.get_embeddings_client(embeddings.OPENAI_EMBEDDING_MODEL)

    assert captured["model"] == embeddings.OPENAI_EMBEDDING_MODEL
    assert captured["dimensions"] == 384
    embeddings.get_embeddings_client.cache_clear()


def test_search_defaults_to_selected_retrieval_depth() -> None:
    request = DocumentSearchRequest(query="What is our return window?")

    assert DEFAULT_RETRIEVAL_TOP_K == 3
    assert request.top_k == DEFAULT_RETRIEVAL_TOP_K


def test_embedding_helpers_use_the_selected_model(monkeypatch) -> None:
    clients = {
        model: FakeEmbeddingsClient(profile.dimensions)
        for model, profile in embeddings.EMBEDDING_PROFILES.items()
    }
    monkeypatch.setattr(
        embeddings,
        "get_embeddings_client",
        lambda model=None: clients[embeddings.get_embedding_profile(model).model],
    )
    embeddings.clear_query_embedding_cache()

    baai_query = embeddings.embed_query("query", embeddings.BAAI_EMBEDDING_MODEL)
    openai_documents = embeddings.embed_documents(
        ["one", "two"],
        embeddings.OPENAI_EMBEDDING_MODEL,
    )

    assert len(baai_query) == 384
    assert [len(item) for item in openai_documents] == [384, 384]


def test_query_embedding_cache_can_be_bypassed(monkeypatch) -> None:
    profile = embeddings.get_embedding_profile()
    client = FakeEmbeddingsClient(profile.dimensions)
    original_embed_query = client.embed_query
    calls = 0

    def embed_query(text: str) -> list[float]:
        nonlocal calls
        calls += 1
        return original_embed_query(text)

    monkeypatch.setattr(client, "embed_query", embed_query)
    monkeypatch.setattr(embeddings, "get_embeddings_client", lambda model=None: client)
    embeddings.clear_query_embedding_cache()

    embeddings.embed_query("same query", use_cache=False)
    embeddings.embed_query("same query", use_cache=False)

    assert calls == 2


def test_unknown_embedding_model_is_rejected() -> None:
    try:
        embeddings.get_embedding_profile("unknown/model")
    except ValueError as exc:
        assert "Unsupported embedding model" in str(exc)
    else:
        raise AssertionError("Unknown embedding model should be rejected")
