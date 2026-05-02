from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_

from app.deps import get_db
from app.db.models import Product
from app.schemas.products import ProductOut
from app.schemas.common import ObjectResponse

router = APIRouter(prefix="/products", tags=["products"])

@router.get("", response_model=ObjectResponse[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, description="Search sku or name"),
    category: str | None = None,
    brand: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Product)

    # Filters
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Product.sku.ilike(like), Product.name.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)

    # Total count (same filters)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Pagination + stable ordering
    stmt = stmt.order_by(Product.sku.asc()).limit(limit).offset(offset)
    items = db.execute(stmt).scalars().all()

    return ObjectResponse[ProductOut](items=items, total=total, limit=limit, offset=offset)
