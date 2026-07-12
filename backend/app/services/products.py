from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Product, ProductImage, ProductReview, ProductSpec, ProductVariant
from app.schemas.common import ObjectResponse
from app.schemas.products import ProductDetailOut, ProductOut


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
        stmt = stmt.where(
            or_(
                Product.sku.ilike(like),
                Product.name.ilike(like),
                Product.brand.ilike(like),
                Product.model_number.ilike(like),
                Product.short_description.ilike(like),
                Product.long_description.ilike(like),
            )
        )
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


def get_product_detail(*, db: Session, product_id: UUID) -> ProductDetailOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    variants = db.execute(
        select(ProductVariant)
        .where(ProductVariant.product_id == product_id)
        .order_by(ProductVariant.sku.asc())
    ).scalars().all()
    images = db.execute(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.position.asc())
    ).scalars().all()
    specs = db.execute(
        select(ProductSpec)
        .where(ProductSpec.product_id == product_id)
        .order_by(ProductSpec.group_name.asc(), ProductSpec.position.asc())
    ).scalars().all()
    reviews = db.execute(
        select(ProductReview)
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
        .limit(8)
    ).scalars().all()

    return ProductDetailOut.model_validate(
        {
            **ProductOut.model_validate(product).model_dump(),
            "variants": variants,
            "images": images,
            "specs": specs,
            "reviews": reviews,
        }
    )
