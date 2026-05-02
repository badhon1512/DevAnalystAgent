from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import join, select, func, or_
from app.deps import get_db
from app.db.models import Inventory, Product, Warehouse
from app.schemas.inventories import InventoryOut
from app.schemas.common import ObjectResponse

router = APIRouter(prefix="/inventory", tags=["inventories"])

@router.get("", response_model=ObjectResponse[InventoryOut])
def list_inventories(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    warehouse_code: str | None = Query(default=None),
    low_stock: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base_from = (
    join(Inventory, Product, Inventory.product_id == Product.product_id)
    .join(Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id)
    )

    stmt = (
        select(
            Inventory.inventory_id,
            Inventory.product_id,
            Inventory.warehouse_id,
            Inventory.stock_on_hand,
            Inventory.reorder_point,
            Inventory.updated_at,
            Product.sku,
            Product.name.label("product_name"),
            Warehouse.code.label("warehouse_name"),
        )
        .select_from(base_from)
    )

    # ---------- FILTERS ----------
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.name.ilike(like),
            )
        )

    if warehouse_code:
        stmt = stmt.where(Warehouse.code == warehouse_code)

    if low_stock is not None:
        if low_stock:
            stmt = stmt.where(Inventory.stock_on_hand <= Inventory.reorder_point)
        else:
            stmt = stmt.where(Inventory.stock_on_hand > Inventory.reorder_point)

    # ---------- COUNT ----------
    count_stmt = (
        select(func.count(func.distinct(Inventory.inventory_id)))
        .select_from(base_from)
    )

    # apply same filters to count
    if search:
        like = f"%{search}%"
        count_stmt = count_stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.name.ilike(like),
            )
        )

    if warehouse_code:
        count_stmt = count_stmt.where(Warehouse.code == warehouse_code)

    if low_stock is not None:
        if low_stock:
            count_stmt = count_stmt.where(Inventory.stock_on_hand <= Inventory.reorder_point)
        else:
            count_stmt = count_stmt.where(Inventory.stock_on_hand > Inventory.reorder_point)

    total = db.execute(count_stmt).scalar_one()

    # ---------- PAGINATION ----------
    stmt = (
        stmt
        .order_by(Product.sku.asc())
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(stmt).mappings().all()

    items = [InventoryOut(**r) for r in rows]

    return ObjectResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
