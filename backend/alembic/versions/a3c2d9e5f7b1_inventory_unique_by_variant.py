"""inventory unique by variant

Revision ID: a3c2d9e5f7b1
Revises: 9b8f2a1d4c6e
Create Date: 2026-07-11 04:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "a3c2d9e5f7b1"
down_revision: Union[str, None] = "9b8f2a1d4c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_inventory_product_warehouse", "inventory", type_="unique")
    op.create_unique_constraint(
        "uq_inventory_variant_warehouse",
        "inventory",
        ["variant_id", "warehouse_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_inventory_variant_warehouse", "inventory", type_="unique")
    op.create_unique_constraint(
        "uq_inventory_product_warehouse",
        "inventory",
        ["product_id", "warehouse_id"],
    )
