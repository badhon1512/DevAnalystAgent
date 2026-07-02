from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.common import ObjectResponse
from app.schemas.products import ProductOut
from app.services.products import list_products as list_products_service

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
    return list_products_service(
        db=db,
        search=search,
        category=category,
        brand=brand,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
