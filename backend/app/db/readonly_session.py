import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker

from app.db.session import DATABASE_URL


AGENT_READONLY_DATABASE_URL = os.getenv("AGENT_READONLY_DATABASE_URL") or DATABASE_URL
AGENT_VIEW_SCHEMA = "agent_views"
AGENT_VIEW_NAMES = frozenset(
    {
        "categories",
        "competitor_prices",
        "inventory",
        "market_signals",
        "product_images",
        "product_reviews",
        "product_specs",
        "product_variants",
        "products",
        "returns",
        "sales",
        "warehouses",
    }
)

readonly_engine = create_engine(
    AGENT_READONLY_DATABASE_URL,
    pool_pre_ping=True,
)


def enforce_readonly_transaction(connection: Connection) -> None:
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        connection.exec_driver_sql(
            f"SET LOCAL search_path TO {AGENT_VIEW_SCHEMA}"
        )


event.listen(readonly_engine, "begin", enforce_readonly_transaction)

ReadOnlySessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=readonly_engine,
)
