import re
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from sqlalchemy import text
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from app.db.session import SessionLocal, engine

from app.schemas.db_info import DatabaseInfo, TableInfo, ColumnInfo, ForeignKeyInfo, IndexInfo


# If you ever store PII later, you can list tables/columns to hide:
SENSITIVE_TABLES: set[str] = set()
SENSITIVE_COLUMNS: set[str] = {
    "email",
    "phone",
    "address",
    "customer_name",
    "first_name",
    "last_name",
}

MAX_SQL_ROWS = 200
READONLY_SQL_START_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
BLOCKED_SQL_RE = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|truncate|merge|grant|revoke|"
    r"copy|call|execute|do|vacuum|analyze|refresh|lock|set|reset"
    r")\b",
    re.IGNORECASE,
)


def _safe_type(col_type) -> str:
    # SQLAlchemy types can be verbose; stringify is fine for agent use
    return str(col_type)


def _should_hide_column(col_name: str) -> bool:
    return col_name.lower() in SENSITIVE_COLUMNS


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _validate_readonly_sql(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty SQL string")

    normalized = query.strip()
    without_trailing_semicolon = normalized[:-1].strip() if normalized.endswith(";") else normalized

    if ";" in without_trailing_semicolon:
        raise ValueError("Only one SQL statement is allowed")
    if not READONLY_SQL_START_RE.match(without_trailing_semicolon):
        raise ValueError("Only SELECT or WITH queries are allowed")
    if BLOCKED_SQL_RE.search(without_trailing_semicolon):
        raise ValueError("Query contains a blocked SQL keyword")

    return without_trailing_semicolon


def get_db_info(
    *,
    db: Session,
    engine: Engine,
    include_row_counts: bool = True,
    max_tables: int = 50,
) -> DatabaseInfo:
    """
    Read-only schema/stats tool for the agent.

    Safe by default:
    - returns schema metadata (tables/cols/keys/indexes)
    - optional row counts
    - NO raw data rows
    """
    inspector = inspect(engine)
    dialect = engine.dialect.name

    tables = inspector.get_table_names(schema="public")
    tables = sorted(tables)[:max_tables]

    out_tables: list[TableInfo] = []

    for t in tables:
        if t in SENSITIVE_TABLES:
            continue

        cols = []
        for c in inspector.get_columns(t, schema="public"):
            col_name = c.get("name", "")
            if _should_hide_column(col_name):
                # Hide potentially sensitive columns from the agent entirely
                continue

            cols.append(
                ColumnInfo(
                    name=col_name,
                    type=_safe_type(c.get("type")),
                    nullable=bool(c.get("nullable", True)),
                    default=str(c.get("default")) if c.get("default") is not None else None,
                )
            )

        pk = inspector.get_pk_constraint(t, schema="public") or {}
        pk_cols = pk.get("constrained_columns") or []

        fks = []
        for fk in inspector.get_foreign_keys(t, schema="public") or []:
            constrained = fk.get("constrained_columns") or []
            referred_table = fk.get("referred_table") or ""
            referred_cols = fk.get("referred_columns") or []
            for i, col in enumerate(constrained):
                # Keep 1:1 mapping if possible
                ref_col = referred_cols[i] if i < len(referred_cols) else (referred_cols[0] if referred_cols else "")
                # Hide FK column if it's considered sensitive
                if _should_hide_column(col):
                    continue
                fks.append(ForeignKeyInfo(column=col, references_table=referred_table, references_column=ref_col))

        idxs = []
        for idx in inspector.get_indexes(t, schema="public") or []:
            idx_cols = idx.get("column_names") or []
            # Filter out sensitive columns from index display too
            idx_cols = [c for c in idx_cols if not _should_hide_column(c)]
            idxs.append(IndexInfo(name=idx.get("name") or "", columns=idx_cols, unique=bool(idx.get("unique", False))))

        row_count = None
        if include_row_counts:
            # Row count is safe and very useful for agent planning
            row_count = db.execute(text(f'SELECT COUNT(*) FROM public."{t}"')).scalar_one()

        out_tables.append(
            TableInfo(
                name=t,
                columns=cols,
                primary_key=pk_cols,
                foreign_keys=fks,
                indexes=idxs,
                row_count=row_count,
            )
        )

    return DatabaseInfo(
        dialect=dialect,
        tables=out_tables,
        notes={
            "privacy": "No raw rows returned. Potential PII columns are filtered by allow/deny list.",
            "scope": "public schema only. Limited table count to avoid huge payloads.",
        },
    )



@tool
def get_db_info_tool(include_row_counts: bool = False) -> dict:
    """Return DB schema info (tables/columns/fks/indexes). Optionally include row counts."""
    with SessionLocal() as db:
        return get_db_info(
            db=db,
            engine=engine,
            include_row_counts=include_row_counts,
        ).model_dump()


def get_sql_database_toolkit_tools(llm):
    """Return non-executing SQLDatabaseToolkit tools backed by the app database engine."""
    sql_db = SQLDatabase(
        engine=engine,
        schema="public",
        sample_rows_in_table_info=0,
        indexes_in_table_info=True,
        lazy_table_reflection=True,
    )
    toolkit = SQLDatabaseToolkit(db=sql_db, llm=llm)
    return [tool for tool in toolkit.get_tools() if tool.name != "sql_db_query"]


@tool
def run_readonly_sql_tool(query: str, max_rows: int = 100) -> dict:
    """
    Execute one guarded read-only SELECT/WITH SQL query against the app database.

    Use this for actual DB query execution after checking SQL with sql_db_query_checker.
    Write/DDL statements are rejected before reaching the database.
    """
    safe_query = _validate_readonly_sql(query)
    safe_max_rows = max(1, min(int(max_rows or 100), MAX_SQL_ROWS))

    with engine.connect() as conn:
        result = conn.execute(text(safe_query))
        rows = [
            {
                key: _json_safe(value)
                for key, value in row._mapping.items()
                if not _should_hide_column(key)
            }
            for row in result.fetchmany(safe_max_rows + 1)
        ]

    truncated = len(rows) > safe_max_rows
    if truncated:
        rows = rows[:safe_max_rows]

    return {
        "columns": list(rows[0].keys()) if rows else [],
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "max_rows": safe_max_rows,
    }
