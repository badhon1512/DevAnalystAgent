from unittest.mock import Mock

import pytest

from app.db.readonly_session import enforce_readonly_transaction
from app.tools.db import _validate_readonly_sql


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO products (name) VALUES ('unsafe')",
        "UPDATE products SET name = 'unsafe'",
        "DELETE FROM products",
        "DROP TABLE products",
        "WITH removed AS (DELETE FROM products RETURNING *) SELECT * FROM removed",
        "SELECT * FROM products; DELETE FROM products",
        "SET TRANSACTION READ WRITE",
        "SELECT * FROM public.products",
        "SELECT * FROM chat_users",
        "SELECT * FROM agent_views.conversations",
        "SELECT * FROM/**/public.products",
        "SELECT * FROM products -- JOIN public.chat_users",
    ],
)
def test_rejects_database_write_queries(query: str) -> None:
    with pytest.raises(ValueError):
        _validate_readonly_sql(query)


def test_accepts_single_select_and_with_queries() -> None:
    assert _validate_readonly_sql("SELECT name FROM products;") == (
        "SELECT name FROM products"
    )
    assert _validate_readonly_sql(
        "WITH totals AS (SELECT COUNT(*) AS count FROM products) "
        "SELECT count FROM totals"
    ).startswith("WITH totals")
    assert _validate_readonly_sql(
        "SELECT p.name, SUM(s.quantity) "
        "FROM agent_views.products p "
        "JOIN sales s ON s.product_id = p.product_id "
        "GROUP BY p.name"
    ).startswith("SELECT p.name")


def test_postgres_transactions_are_forced_read_only() -> None:
    connection = Mock()
    connection.dialect.name = "postgresql"

    enforce_readonly_transaction(connection)

    assert connection.exec_driver_sql.call_args_list == [
        (("SET TRANSACTION READ ONLY",),),
        (("SET LOCAL search_path TO agent_views",),),
    ]


def test_non_postgres_connections_skip_postgres_statement() -> None:
    connection = Mock()
    connection.dialect.name = "sqlite"

    enforce_readonly_transaction(connection)

    connection.exec_driver_sql.assert_not_called()
