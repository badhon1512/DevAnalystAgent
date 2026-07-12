"""add branch location details

Revision ID: b4e6a8c1d2f3
Revises: a3c2d9e5f7b1
Create Date: 2026-07-11 04:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e6a8c1d2f3"
down_revision: Union[str, None] = "a3c2d9e5f7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("warehouses", sa.Column("postal_code", sa.String(), nullable=True))
    op.add_column("warehouses", sa.Column("street_address", sa.Text(), nullable=True))
    op.add_column("warehouses", sa.Column("region", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("warehouses", "region")
    op.drop_column("warehouses", "street_address")
    op.drop_column("warehouses", "postal_code")
