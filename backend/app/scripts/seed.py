import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db import models  # ensures model classes are loaded


# -----------------------------
# Config (tune these freely)
# -----------------------------
DEFAULTS = {
    "products": 200,
    "warehouses": 3,
    "sales": 6000,
    "days": 90,
    "return_rate": 0.03,  # 3%
    "top_seller_share": 0.20,  # 20% products drive most sales (Pareto-ish)
    "seed": 42,
}


CATEGORIES = [
    "Electronics",
    "Home",
    "Kitchen",
    "Sports",
    "Beauty",
    "Office",
    "Toys",
    "Automotive",
]
BRANDS = [
    "NovaWorks",
    "Astra",
    "Kraftly",
    "ZenCore",
    "NordicLine",
    "BrightCo",
    "OmniPeak",
]
REGIONS = ["DE-BY", "DE-BE", "DE-NW", "DE-HE", "DE-HH", "DE-BW", "DE-SN"]
CHANNELS = ["online", "retail", "b2b"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # store naive UTC


def make_sku(i: int) -> str:
    return f"SKU-{i:05d}"


def weighted_choice(items, weights):
    # Python 3.11 has random.choices; keeping explicit wrapper
    return random.choices(items, weights=weights, k=1)[0]


def ensure_clean_start(db: Session):
    """
    Clear tables in safe order for reseeding.
    This is a 'dev-only' seeding helper.
    """
    db.execute(text("TRUNCATE TABLE returns RESTART IDENTITY CASCADE;"))
    db.execute(text("TRUNCATE TABLE sales RESTART IDENTITY CASCADE;"))
    db.execute(text("TRUNCATE TABLE inventory RESTART IDENTITY CASCADE;"))
    db.execute(text("TRUNCATE TABLE warehouses RESTART IDENTITY CASCADE;"))
    db.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE;"))
    db.commit()


def seed_products(db: Session, n: int):
    products = []
    for i in range(1, n + 1):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS)

        # realistic-ish pricing
        base_price = random.uniform(9.0, 250.0)
        price = round(base_price, 2)
        cost = round(price * random.uniform(0.45, 0.75), 2)

        products.append(
            models.Product(
                sku=make_sku(i),
                name=f"{brand} {category} Item {i}",
                category=category,
                brand=brand,
                currency="EUR",
                price=price,
                cost=cost,
                is_active=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )

    db.add_all(products)
    db.commit()
    return products


def seed_warehouses(db: Session, n: int):
    # A few realistic German warehouse locations
    candidates = [
        ("WH-MUC", "Munich Fulfillment", "Munich", "DE"),
        ("WH-BER", "Berlin Hub", "Berlin", "DE"),
        ("WH-FRA", "Frankfurt DC", "Frankfurt", "DE"),
        ("WH-HAM", "Hamburg Warehouse", "Hamburg", "DE"),
    ]
    chosen = candidates[:n]

    warehouses = []
    for code, name, city, country in chosen:
        warehouses.append(
            models.Warehouse(
                code=code,
                name=name,
                city=city,
                country=country,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )

    db.add_all(warehouses)
    db.commit()
    return warehouses


def seed_inventory(db: Session, products, warehouses):
    rows = []
    for p in products:
        # some products are naturally lower stock / higher stock
        base = random.randint(20, 300)
        reorder_point = random.randint(10, 60)

        for w in warehouses:
            # vary stock by warehouse
            stock = max(0, int(random.gauss(mu=base, sigma=base * 0.25)))
            rows.append(
                models.Inventory(
                    product_id=p.product_id,
                    warehouse_id=w.warehouse_id,
                    stock_on_hand=stock,
                    reorder_point=reorder_point,
                    updated_at=utcnow(),
                )
            )

    db.add_all(rows)
    db.commit()
    return rows


def seed_sales_and_returns(
    db: Session,
    products,
    warehouses,
    sales_n: int,
    days: int,
    return_rate: float,
    top_seller_share: float,
):
    now = utcnow()
    start = now - timedelta(days=days)

    # Pareto-ish: top products get most sales
    product_ids = [p.product_id for p in products]
    top_k = max(5, int(len(products) * top_seller_share))
    top_ids = set(product_ids[:top_k])

    # Build weights: top products heavier
    weights = []
    for pid in product_ids:
        weights.append(8.0 if pid in top_ids else 1.0)

    wh_ids = [w.warehouse_id for w in warehouses]

    sales_rows = []
    for _ in range(sales_n):
        pid = weighted_choice(product_ids, weights)

        # sold_at: skew more recent days slightly
        day_offset = int(random.triangular(0, days, days * 0.65))
        sold_at = start + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

        # channel distribution: online dominates
        channel = random.choices(CHANNELS, weights=[0.65, 0.25, 0.10], k=1)[0]
        region = random.choice(REGIONS)

        # quantities: b2b tends higher
        if channel == "b2b":
            qty = random.randint(5, 30)
        elif channel == "retail":
            qty = random.randint(1, 6)
        else:
            qty = random.randint(1, 4)

        # use product list order to fetch base price quickly
        # (we can map product_id -> price)
        sales_rows.append(
            {
                "sale_id": uuid.uuid4(),
                "sold_at": sold_at,
                "product_id": pid,
                "warehouse_id": random.choice(wh_ids),
                "quantity": qty,
                "channel": channel,
                "region": region,
                "created_at": now,
            }
        )

    # Map product_id -> price
    price_map = {p.product_id: float(p.price) for p in products}

    sales_models = []
    for r in sales_rows:
        base_price = price_map[r["product_id"]]

        # small channel price variation + random discount
        if r["channel"] == "b2b":
            unit_price = round(base_price * random.uniform(0.80, 0.95), 2)
        elif r["channel"] == "retail":
            unit_price = round(base_price * random.uniform(0.95, 1.05), 2)
        else:
            unit_price = round(base_price * random.uniform(0.90, 1.00), 2)

        revenue = round(unit_price * r["quantity"], 2)

        sales_models.append(
            models.Sale(
                sale_id=r["sale_id"],
                sold_at=r["sold_at"],
                product_id=r["product_id"],
                warehouse_id=r["warehouse_id"],
                quantity=r["quantity"],
                unit_price=unit_price,
                revenue=revenue,
                channel=r["channel"],
                region=r["region"],
                created_at=r["created_at"],
            )
        )

    db.add_all(sales_models)
    db.commit()

    # Returns: sample some sales rows
    returns_n = int(len(sales_models) * return_rate)
    sampled_sales = random.sample(sales_models, k=max(1, returns_n))

    reasons = ["damaged", "wrong item", "not needed", "late delivery", "quality issue"]
    return_models = []
    for s in sampled_sales:
        # return after 1-21 days
        returned_at = s.sold_at + timedelta(days=random.randint(1, 21))
        return_qty = 1 if s.quantity == 1 else random.randint(1, min(2, s.quantity))
        return_models.append(
            models.Return(
                returned_at=returned_at,
                sale_id=s.sale_id,
                product_id=s.product_id,
                quantity=return_qty,
                reason=random.choice(reasons),
                created_at=utcnow(),
            )
        )

    db.add_all(return_models)
    db.commit()

    return len(sales_models), len(return_models)


def main():
    # Read from env overrides (optional)
    cfg = dict(DEFAULTS)
    cfg["products"] = int(os.getenv("SEED_PRODUCTS", cfg["products"]))
    cfg["warehouses"] = int(os.getenv("SEED_WAREHOUSES", cfg["warehouses"]))
    cfg["sales"] = int(os.getenv("SEED_SALES", cfg["sales"]))
    cfg["days"] = int(os.getenv("SEED_DAYS", cfg["days"]))
    cfg["return_rate"] = float(os.getenv("SEED_RETURN_RATE", cfg["return_rate"]))
    cfg["seed"] = int(os.getenv("SEED_RANDOM", cfg["seed"]))

    random.seed(cfg["seed"])

    with SessionLocal() as db:
        print("Seeding ProductAI database...")
        ensure_clean_start(db)

        products = seed_products(db, cfg["products"])
        warehouses = seed_warehouses(db, cfg["warehouses"])
        seed_inventory(db, products, warehouses)

        sales_n, returns_n = seed_sales_and_returns(
            db,
            products,
            warehouses,
            sales_n=cfg["sales"],
            days=cfg["days"],
            return_rate=cfg["return_rate"],
            top_seller_share=cfg["top_seller_share"],
        )

        print(f"Done products={len(products)} warehouses={len(warehouses)} inventory={len(products)*len(warehouses)} sales={sales_n} returns={returns_n}")


if __name__ == "__main__":
    main()
