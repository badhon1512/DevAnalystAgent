"""add BAAI chunk embeddings

Revision ID: a9c4e7f2b1d6
Revises: d8b2f4c6a1e3
Create Date: 2026-08-07 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a9c4e7f2b1d6"
down_revision: Union[str, None] = "d8b2f4c6a1e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN embedding_baai vector(384)"
    )
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_baai
        ON document_chunks
        USING hnsw (embedding_baai vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_embedding_baai",
        table_name="document_chunks",
    )
    op.drop_column("document_chunks", "embedding_baai")
    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding SET NOT NULL"
    )
