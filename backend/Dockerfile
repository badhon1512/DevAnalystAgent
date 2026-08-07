FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"
ENV FASTEMBED_CACHE_PATH=/app/.cache/fastembed
ENV RAG_EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/.cache/fastembed')"

COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY app ./app
COPY evals ./evals

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.reindex_embeddings --model BAAI/bge-small-en-v1.5 && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
