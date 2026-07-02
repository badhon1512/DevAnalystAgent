from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.schemas.common import ObjectResponse
from app.schemas.inventories import InventoryOut
from app.services.inventories import list_inventories as list_inventories_service

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
    return list_inventories_service(
        db=db,
        search=search,
        warehouse_code=warehouse_code,
        low_stock=low_stock,
        limit=limit,
        offset=offset,
    )
