"""shorten OpenAI chunk embeddings to 384 dimensions

Revision ID: b7d3e9f1a2c4
Revises: a9c4e7f2b1d6
Create Date: 2026-08-08 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b7d3e9f1a2c4"
down_revision: Union[str, None] = "a9c4e7f2b1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_document_chunks_embedding"


def _rebuild_index() -> None:
    op.execute(
        f"""
        CREATE INDEX {INDEX_NAME}
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def upgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunks")
    op.execute(
        """
        ALTER TABLE document_chunks
        ALTER COLUMN embedding TYPE vector(384)
        USING NULL::vector(384)
        """
    )
    _rebuild_index()


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunks")
    op.execute(
        """
        ALTER TABLE document_chunks
        ALTER COLUMN embedding TYPE vector(1536)
        USING NULL::vector(1536)
        """
    )
    _rebuild_index()
