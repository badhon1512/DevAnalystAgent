from pydantic import BaseModel


class DashboardMetric(BaseModel):
    label: str
    value: float | int | str
    detail: str
    tone: str = "neutral"


class RevenuePoint(BaseModel):
    label: str
    revenue: float


class CategoryDemand(BaseModel):
    label: str
    units: int
    revenue: float
    share: float


class BranchRisk(BaseModel):
    branch: str
    city: str | None = None
    stock_on_hand: int
    reorder_point: int
    coverage: float
    low_stock_skus: int
    risk: str


class ProductInsight(BaseModel):
    product_id: str
    name: str
    category: str | None = None
    units: int
    revenue: float


class ChannelInsight(BaseModel):
    channel: str
    revenue: float
    share: float


class ReturnInsight(BaseModel):
    returned_units: int
    sold_units: int
    return_rate: float
    top_reasons: list[DashboardMetric]


class DashboardAnalytics(BaseModel):
    generated_at: str
    metrics: list[DashboardMetric]
    revenue_trend: list[RevenuePoint]
    category_demand: list[CategoryDemand]
    branch_risk: list[BranchRisk]
    top_products: list[ProductInsight]
    channel_mix: list[ChannelInsight]
    returns: ReturnInsight
