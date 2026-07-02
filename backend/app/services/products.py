from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Product
from app.schemas.common import ObjectResponse
from app.schemas.products import ProductOut


def list_products(
    *,
    db: Session,
    search: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ObjectResponse[ProductOut]:
    stmt = select(Product)

    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Product.sku.ilike(like), Product.name.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Product.sku.asc()).limit(limit).offset(offset)
    items = db.execute(stmt).scalars().all()

    return ObjectResponse[ProductOut](items=items, total=total, limit=limit, offset=offset)
