from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session

from app.db.models import Inventory, Product, Return, Sale, Warehouse
from app.deps import get_db
from app.schemas.analytics import (
    BranchRisk,
    CategoryDemand,
    ChannelInsight,
    DashboardAnalytics,
    DashboardMetric,
    ProductInsight,
    ReturnInsight,
    RevenuePoint,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def as_float(value: object) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def as_int(value: object) -> int:
    return int(value or 0)


def pct(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(part * 100 / total, 1)


def money(value: float) -> str:
    if value >= 1_000_000:
        return f"€{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"€{value / 1_000:.1f}K"
    return f"€{value:.0f}"


@router.get("/dashboard", response_model=DashboardAnalytics)
def dashboard_analytics(db: Session = Depends(get_db)) -> DashboardAnalytics:
    now = datetime.utcnow()
    current_start = now - timedelta(days=30)
    previous_start = now - timedelta(days=60)
    six_month_start = now - timedelta(days=180)

    total_revenue = as_float(db.scalar(select(func.coalesce(func.sum(Sale.revenue), 0))))
    total_units = as_int(db.scalar(select(func.coalesce(func.sum(Sale.quantity), 0))))
    current_revenue = as_float(
        db.scalar(select(func.coalesce(func.sum(Sale.revenue), 0)).where(Sale.sold_at >= current_start))
    )
    previous_revenue = as_float(
        db.scalar(
            select(func.coalesce(func.sum(Sale.revenue), 0)).where(
                Sale.sold_at >= previous_start,
                Sale.sold_at < current_start,
            )
        )
    )
    growth = round(((current_revenue - previous_revenue) / previous_revenue) * 100, 1) if previous_revenue else 0.0

    low_stock_count = as_int(
        db.scalar(select(func.count()).select_from(Inventory).where(Inventory.stock_on_hand <= Inventory.reorder_point))
    )

    revenue_rows = db.execute(
        select(
            func.date_trunc("month", Sale.sold_at).label("month"),
            func.coalesce(func.sum(Sale.revenue), 0).label("revenue"),
        )
        .where(Sale.sold_at >= six_month_start)
        .group_by("month")
        .order_by("month")
    ).all()
    revenue_trend = [
        RevenuePoint(label=row.month.strftime("%b"), revenue=round(as_float(row.revenue), 2))
        for row in revenue_rows
    ]

    demand_rows = db.execute(
        select(
            func.coalesce(Product.category, "Uncategorized").label("category"),
            func.coalesce(func.sum(Sale.quantity), 0).label("units"),
            func.coalesce(func.sum(Sale.revenue), 0).label("revenue"),
        )
        .join(Product, Product.product_id == Sale.product_id)
        .group_by("category")
        .order_by(desc("units"))
        .limit(6)
    ).all()
    top_units = max([as_int(row.units) for row in demand_rows] or [0])
    category_demand = [
        CategoryDemand(
            label=row.category,
            units=as_int(row.units),
            revenue=round(as_float(row.revenue), 2),
            share=pct(as_int(row.units), top_units),
        )
        for row in demand_rows
    ]

    branch_rows = db.execute(
        select(
            Warehouse.name.label("branch"),
            Warehouse.city.label("city"),
            func.coalesce(func.sum(Inventory.stock_on_hand), 0).label("stock_on_hand"),
            func.coalesce(func.sum(Inventory.reorder_point), 0).label("reorder_point"),
            func.coalesce(
                func.sum(
                    case(
                        (Inventory.stock_on_hand <= Inventory.reorder_point, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("low_stock_skus"),
        )
        .join(Warehouse, Warehouse.warehouse_id == Inventory.warehouse_id)
        .group_by(Warehouse.warehouse_id, Warehouse.name, Warehouse.city)
        .order_by(desc("low_stock_skus"))
    ).all()
    branch_risk: list[BranchRisk] = []
    for row in branch_rows:
        stock = as_int(row.stock_on_hand)
        reorder = as_int(row.reorder_point)
        coverage = pct(stock, reorder) if reorder else 100.0
        low_stock_skus = as_int(row.low_stock_skus)
        risk = "High" if coverage < 80 or low_stock_skus >= 8 else "Medium" if coverage < 130 or low_stock_skus >= 3 else "Low"
        branch_risk.append(
            BranchRisk(
                branch=row.branch,
                city=row.city,
                stock_on_hand=stock,
                reorder_point=reorder,
                coverage=min(coverage, 200.0),
                low_stock_skus=low_stock_skus,
                risk=risk,
            )
        )

    product_rows = db.execute(
        select(
            Product.product_id,
            Product.name,
            Product.category,
            func.coalesce(func.sum(Sale.quantity), 0).label("units"),
            func.coalesce(func.sum(Sale.revenue), 0).label("revenue"),
        )
        .join(Product, Product.product_id == Sale.product_id)
        .group_by(Product.product_id, Product.name, Product.category)
        .order_by(desc("revenue"))
        .limit(5)
    ).all()
    top_products = [
        ProductInsight(
            product_id=str(row.product_id),
            name=row.name,
            category=row.category,
            units=as_int(row.units),
            revenue=round(as_float(row.revenue), 2),
        )
        for row in product_rows
    ]

    channel_rows = db.execute(
        select(
            Sale.channel,
            func.coalesce(func.sum(Sale.revenue), 0).label("revenue"),
        )
        .group_by(Sale.channel)
        .order_by(desc("revenue"))
    ).all()
    channel_mix = [
        ChannelInsight(
            channel=row.channel,
            revenue=round(as_float(row.revenue), 2),
            share=pct(as_float(row.revenue), total_revenue),
        )
        for row in channel_rows
    ]

    returned_units = as_int(db.scalar(select(func.coalesce(func.sum(Return.quantity), 0))))
    return_rate = pct(returned_units, total_units)
    reason_rows = db.execute(
        select(
            func.coalesce(Return.reason, "Unspecified").label("reason"),
            func.coalesce(func.sum(Return.quantity), 0).label("units"),
        )
        .group_by("reason")
        .order_by(desc("units"))
        .limit(3)
    ).all()

    metrics = [
        DashboardMetric(
            label="Revenue",
            value=money(total_revenue),
            detail=f"{growth:+.1f}% vs previous 30 days",
            tone="good" if growth >= 0 else "danger",
        ),
        DashboardMetric(label="Units sold", value=total_units, detail="Across all channels", tone="neutral"),
        DashboardMetric(label="Low-stock SKUs", value=low_stock_count, detail="At or below reorder point", tone="danger" if low_stock_count else "good"),
        DashboardMetric(label="Return rate", value=f"{return_rate:.1f}%", detail=f"{returned_units} returned units", tone="warn" if return_rate > 8 else "good"),
    ]

    return DashboardAnalytics(
        generated_at=now.isoformat(),
        metrics=metrics,
        revenue_trend=revenue_trend,
        category_demand=category_demand,
        branch_risk=branch_risk,
        top_products=top_products,
        channel_mix=channel_mix,
        returns=ReturnInsight(
            returned_units=returned_units,
            sold_units=total_units,
            return_rate=return_rate,
            top_reasons=[
                DashboardMetric(label=row.reason, value=as_int(row.units), detail="returned units")
                for row in reason_rows
            ],
        ),
    )
