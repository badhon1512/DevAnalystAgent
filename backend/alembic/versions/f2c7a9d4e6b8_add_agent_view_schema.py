"""add agent view schema

Revision ID: f2c7a9d4e6b8
Revises: e8f4a2c6d9b1
Create Date: 2026-07-27 23:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f2c7a9d4e6b8"
down_revision: Union[str, None] = "e8f4a2c6d9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VIEW_DEFINITIONS = {
    "categories": """
        SELECT category_id, parent_category_id, name, slug, description,
               created_at, updated_at
        FROM public.categories
    """,
    "products": """
        SELECT product_id, category_id, sku, name, slug, short_description,
               long_description, category, brand, manufacturer, model_number,
               tags, use_cases, target_audience, warranty_months,
               return_window_days, care_instructions, compatibility_notes,
               included_accessories, safety_notes, currency, price, cost,
               is_active, created_at, updated_at
        FROM public.products
    """,
    "product_variants": """
        SELECT variant_id, product_id, sku, title, color, size, material,
               ram_gb, storage_gb, storage_type, processor, gpu, display_size,
               battery_life_hours, option_values, price, cost, currency,
               barcode, is_active, created_at, updated_at
        FROM public.product_variants
    """,
    "product_images": """
        SELECT image_id, product_id, variant_id, url, alt_text, position,
               is_primary
        FROM public.product_images
    """,
    "product_specs": """
        SELECT spec_id, product_id, variant_id, group_name, name, value, unit,
               position
        FROM public.product_specs
    """,
    "product_reviews": """
        SELECT review_id, product_id, variant_id, rating, title, body,
               sentiment, created_at
        FROM public.product_reviews
    """,
    "competitor_prices": """
        SELECT competitor_price_id, product_id, variant_id, competitor_name,
               competitor_product_url, price, currency, observed_at
        FROM public.competitor_prices
    """,
    "market_signals": """
        SELECT signal_id, product_id, category_id, signal_type, region, value,
               confidence, notes, observed_at
        FROM public.market_signals
    """,
    "warehouses": """
        SELECT warehouse_id, code, name, city, postal_code, street_address,
               region, country, created_at, updated_at
        FROM public.warehouses
    """,
    "inventory": """
        SELECT inventory_id, product_id, variant_id, warehouse_id,
               stock_on_hand, reorder_point, updated_at
        FROM public.inventory
    """,
    "sales": """
        SELECT sale_id, sold_at, product_id, variant_id, warehouse_id,
               quantity, unit_price, revenue, channel, region, created_at
        FROM public.sales
    """,
    "returns": """
        SELECT return_id, returned_at, sale_id, product_id, variant_id,
               quantity, reason, created_at
        FROM public.returns
    """,
}


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent_views")
    for view_name, select_sql in VIEW_DEFINITIONS.items():
        op.execute(
            f"""
            CREATE OR REPLACE VIEW agent_views.{view_name}
            WITH (security_barrier = true)
            AS {select_sql}
            """
        )


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS agent_views CASCADE")
