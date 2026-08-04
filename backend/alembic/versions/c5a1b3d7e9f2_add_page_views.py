"""add page views

Revision ID: c5a1b3d7e9f2
Revises: f2c7a9d4e6b8
Create Date: 2026-08-03 03:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5a1b3d7e9f2"
down_revision: Union[str, None] = "f2c7a9d4e6b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "page_views",
        sa.Column("view_id", sa.UUID(), nullable=False),
        sa.Column("path", sa.String(length=300), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("visitor_hash", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("view_id"),
    )
    op.create_index("ix_page_views_created_at", "page_views", ["created_at"])
    op.create_index(
        "ix_page_views_path_created_at",
        "page_views",
        ["path", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_page_views_path_created_at", table_name="page_views")
    op.drop_index("ix_page_views_created_at", table_name="page_views")
    op.drop_table("page_views")
