from pydantic import BaseModel, ConfigDict, Field
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


class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    variant_id: UUID
    product_id: UUID
    sku: str
    title: str
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    storage_type: Optional[str] = None
    processor: Optional[str] = None
    gpu: Optional[str] = None
    display_size: Optional[str] = None
    battery_life_hours: Optional[float] = None
    option_values: Optional[dict] = None
    price: float
    cost: Optional[float] = None
    currency: str
    barcode: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    image_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    url: str
    alt_text: Optional[str] = None
    position: int
    is_primary: bool


class ProductSpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    spec_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    group_name: str
    name: str
    value: str
    unit: Optional[str] = None
    position: int


class ProductReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    rating: int
    title: str
    body: str
    sentiment: Optional[str] = None
    created_at: datetime


class ProductDetailOut(ProductOut):
    variants: list[ProductVariantOut] = Field(default_factory=list)
    images: list[ProductImageOut] = Field(default_factory=list)
    specs: list[ProductSpecOut] = Field(default_factory=list)
    reviews: list[ProductReviewOut] = Field(default_factory=list)
