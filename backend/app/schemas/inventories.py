from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventory_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    warehouse_id: UUID
    sku: Optional[str] = None
    variant_sku: Optional[str] = None
    product_name: Optional[str] = None
    variant_title: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_city: Optional[str] = None
    warehouse_postal_code: Optional[str] = None
    warehouse_region: Optional[str] = None
    warehouse_country: Optional[str] = None
    stock_on_hand: int
    reorder_point: int
    updated_at: datetime

   
