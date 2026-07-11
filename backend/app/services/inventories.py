from sqlalchemy import func, join, or_, outerjoin, select
from sqlalchemy.orm import Session

from app.db.models import Inventory, Product, ProductVariant, Warehouse
from app.schemas.common import ObjectResponse
from app.schemas.inventories import InventoryOut


def _apply_inventory_filters(
    stmt,
    *,
    search: str | None,
    warehouse_code: str | None,
    low_stock: bool | None,
):
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.name.ilike(like),
                ProductVariant.sku.ilike(like),
                ProductVariant.title.ilike(like),
            )
        )

    if warehouse_code:
        stmt = stmt.where(Warehouse.code == warehouse_code)

    if low_stock is not None:
        if low_stock:
            stmt = stmt.where(Inventory.stock_on_hand <= Inventory.reorder_point)
        else:
            stmt = stmt.where(Inventory.stock_on_hand > Inventory.reorder_point)

    return stmt


def list_inventories(
    *,
    db: Session,
    search: str | None = None,
    warehouse_code: str | None = None,
    low_stock: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ObjectResponse[InventoryOut]:
    base_from = outerjoin(
        join(Inventory, Product, Inventory.product_id == Product.product_id),
        ProductVariant,
        Inventory.variant_id == ProductVariant.variant_id,
    ).join(
        Warehouse,
        Inventory.warehouse_id == Warehouse.warehouse_id,
    )

    stmt = select(
        Inventory.inventory_id,
        Inventory.product_id,
        Inventory.variant_id,
        Inventory.warehouse_id,
        Inventory.stock_on_hand,
        Inventory.reorder_point,
        Inventory.updated_at,
        Product.sku,
        ProductVariant.sku.label("variant_sku"),
        Product.name.label("product_name"),
        ProductVariant.title.label("variant_title"),
        Warehouse.code.label("warehouse_name"),
        Warehouse.city.label("warehouse_city"),
        Warehouse.postal_code.label("warehouse_postal_code"),
        Warehouse.region.label("warehouse_region"),
        Warehouse.country.label("warehouse_country"),
    ).select_from(base_from)
    stmt = _apply_inventory_filters(
        stmt,
        search=search,
        warehouse_code=warehouse_code,
        low_stock=low_stock,
    )

    count_stmt = select(func.count(func.distinct(Inventory.inventory_id))).select_from(base_from)
    count_stmt = _apply_inventory_filters(
        count_stmt,
        search=search,
        warehouse_code=warehouse_code,
        low_stock=low_stock,
    )
    total = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Product.sku.asc()).limit(limit).offset(offset)
    rows = db.execute(stmt).mappings().all()
    items = [InventoryOut(**row) for row in rows]

    return ObjectResponse(items=items, total=total, limit=limit, offset=offset)
