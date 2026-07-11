from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    category_id: Optional[UUID] = None
    sku: str
    name: str
    slug: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    tags: Optional[list[str]] = None
    use_cases: Optional[list[str]] = None
    target_audience: Optional[str] = None
    warranty_months: Optional[int] = None
    return_window_days: Optional[int] = None
    care_instructions: Optional[str] = None
    compatibility_notes: Optional[str] = None
    included_accessories: Optional[list[str]] = None
    safety_notes: Optional[str] = None
    currency: str
    price: float
    cost: Optional[float] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
