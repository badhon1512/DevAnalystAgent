"""add conversation users and active flag

Revision ID: d1e2f3a4b5c6
Revises: b4e6a8c1d2f3
Create Date: 2026-07-12 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "b4e6a8c1d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_users",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_chat_users_username"), "chat_users", ["username"], unique=True)
    op.add_column("conversations", sa.Column("user_id", sa.UUID(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_foreign_key(
        "fk_conversations_user_id_chat_users",
        "conversations",
        "chat_users",
        ["user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.alter_column("conversations", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_conversations_user_id_chat_users", "conversations", type_="foreignkey")
    op.drop_column("conversations", "is_active")
    op.drop_column("conversations", "user_id")
    op.drop_index(op.f("ix_chat_users_username"), table_name="chat_users")
    op.drop_table("chat_users")
