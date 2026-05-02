from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    sku: str
    name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    currency: str
    price: float
    cost: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
