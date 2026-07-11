"""add marketplace catalog

Revision ID: 9b8f2a1d4c6e
Revises: 7d4a3e9c1b2f
Create Date: 2026-07-11 03:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9b8f2a1d4c6e"
down_revision: Union[str, None] = "7d4a3e9c1b2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("category_id", sa.UUID(), nullable=False),
        sa.Column("parent_category_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_category_id"], ["categories.category_id"]),
        sa.PrimaryKeyConstraint("category_id"),
        sa.UniqueConstraint("slug"),
    )

    op.add_column("products", sa.Column("category_id", sa.UUID(), nullable=True))
    op.add_column("products", sa.Column("slug", sa.String(), nullable=True))
    op.add_column("products", sa.Column("short_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("long_description", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("manufacturer", sa.String(), nullable=True))
    op.add_column("products", sa.Column("model_number", sa.String(), nullable=True))
    op.add_column("products", sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("use_cases", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("target_audience", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("warranty_months", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("return_window_days", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("care_instructions", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("compatibility_notes", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("included_accessories", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("safety_notes", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_products_slug", "products", ["slug"])
    op.create_foreign_key("fk_products_category_id", "products", "categories", ["category_id"], ["category_id"])

    op.create_table(
        "product_variants",
        sa.Column("variant_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("size", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("ram_gb", sa.Integer(), nullable=True),
        sa.Column("storage_gb", sa.Integer(), nullable=True),
        sa.Column("storage_type", sa.String(), nullable=True),
        sa.Column("processor", sa.String(), nullable=True),
        sa.Column("gpu", sa.String(), nullable=True),
        sa.Column("display_size", sa.String(), nullable=True),
        sa.Column("battery_life_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("option_values", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("barcode", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.PrimaryKeyConstraint("variant_id"),
        sa.UniqueConstraint("sku"),
    )

    op.create_table(
        "product_images",
        sa.Column("image_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.variant_id"]),
        sa.PrimaryKeyConstraint("image_id"),
    )
    op.create_table(
        "product_specs",
        sa.Column("spec_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=True),
        sa.Column("group_name", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.variant_id"]),
        sa.PrimaryKeyConstraint("spec_id"),
    )
    op.create_table(
        "product_reviews",
        sa.Column("review_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.variant_id"]),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_table(
        "competitor_prices",
        sa.Column("competitor_price_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("variant_id", sa.UUID(), nullable=True),
        sa.Column("competitor_name", sa.String(), nullable=False),
        sa.Column("competitor_product_url", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.variant_id"]),
        sa.PrimaryKeyConstraint("competitor_price_id"),
    )
    op.create_table(
        "market_signals",
        sa.Column("signal_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.category_id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.product_id"]),
        sa.PrimaryKeyConstraint("signal_id"),
    )

    op.add_column("inventory", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.add_column("sales", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.add_column("returns", sa.Column("variant_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_inventory_variant_id", "inventory", "product_variants", ["variant_id"], ["variant_id"])
    op.create_foreign_key("fk_sales_variant_id", "sales", "product_variants", ["variant_id"], ["variant_id"])
    op.create_foreign_key("fk_returns_variant_id", "returns", "product_variants", ["variant_id"], ["variant_id"])


def downgrade() -> None:
    op.drop_constraint("fk_returns_variant_id", "returns", type_="foreignkey")
    op.drop_constraint("fk_sales_variant_id", "sales", type_="foreignkey")
    op.drop_constraint("fk_inventory_variant_id", "inventory", type_="foreignkey")
    op.drop_column("returns", "variant_id")
    op.drop_column("sales", "variant_id")
    op.drop_column("inventory", "variant_id")
    op.drop_table("market_signals")
    op.drop_table("competitor_prices")
    op.drop_table("product_reviews")
    op.drop_table("product_specs")
    op.drop_table("product_images")
    op.drop_table("product_variants")
    op.drop_constraint("fk_products_category_id", "products", type_="foreignkey")
    op.drop_constraint("uq_products_slug", "products", type_="unique")
    op.drop_column("products", "safety_notes")
    op.drop_column("products", "included_accessories")
    op.drop_column("products", "compatibility_notes")
    op.drop_column("products", "care_instructions")
    op.drop_column("products", "return_window_days")
    op.drop_column("products", "warranty_months")
    op.drop_column("products", "target_audience")
    op.drop_column("products", "use_cases")
    op.drop_column("products", "tags")
    op.drop_column("products", "model_number")
    op.drop_column("products", "manufacturer")
    op.drop_column("products", "long_description")
    op.drop_column("products", "short_description")
    op.drop_column("products", "slug")
    op.drop_column("products", "category_id")
    op.drop_table("categories")
