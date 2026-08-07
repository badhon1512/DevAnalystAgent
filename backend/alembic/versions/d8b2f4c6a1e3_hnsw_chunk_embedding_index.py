"""replace ivfflat chunk index with hnsw

The ivfflat index was created with lists=100. On a corpus of a few hundred
chunks that leaves roughly one row per list, and pgvector probes a single list
by default, so an index scan returned almost no rows. The failure was silent:
the query succeeded and simply returned fewer matches, or none, whenever the
planner chose the index over a sequential scan.

hnsw has no list count to size against the corpus and gives good recall with
its default ef_search, so it behaves correctly whether the table holds a
hundred chunks or a million.

Revision ID: d8b2f4c6a1e3
Revises: c5a1b3d7e9f2
Create Date: 2026-08-05 01:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d8b2f4c6a1e3"
down_revision: Union[str, None] = "c5a1b3d7e9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_document_chunks_embedding"


def upgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunks")
    op.execute(
        f"""
        CREATE INDEX {INDEX_NAME}
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="document_chunks")
    op.execute(
        f"""
        CREATE INDEX {INDEX_NAME}
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )
