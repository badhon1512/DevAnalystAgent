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
from app.db.readonly_session import (
    AGENT_VIEW_SCHEMA,
    AGENT_VIEW_NAMES,
    ReadOnlySessionLocal,
    readonly_engine,
)

from app.schemas.db_info import ColumnInfo, DatabaseInfo, TableInfo


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
SQL_IDENTIFIER = r'(?:"[^"]+"|[A-Za-z_][A-Za-z0-9_$]*)'
RELATION_RE = re.compile(
    rf"\b(?:from|join)\s+(?P<relation>{SQL_IDENTIFIER}"
    rf"(?:\s*\.\s*{SQL_IDENTIFIER})?)",
    re.IGNORECASE,
)
CTE_NAME_RE = re.compile(
    rf"(?:\bwith|,)\s*(?P<name>{SQL_IDENTIFIER})\s+as\s*\(",
    re.IGNORECASE,
)
SQL_COMMENT_RE = re.compile(r"--|/\*|\*/")


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


def _normalize_sql_identifier(identifier: str) -> str:
    return identifier.strip().strip('"').lower()


def _validate_view_relations(query: str) -> None:
    cte_names = {
        _normalize_sql_identifier(match.group("name"))
        for match in CTE_NAME_RE.finditer(query)
    }
    for match in RELATION_RE.finditer(query):
        relation = match.group("relation")
        identifiers = [
            _normalize_sql_identifier(part)
            for part in re.split(r"\s*\.\s*", relation)
        ]
        if len(identifiers) == 2:
            schema, object_name = identifiers
            if schema != AGENT_VIEW_SCHEMA or object_name not in AGENT_VIEW_NAMES:
                raise ValueError(
                    "Queries may access only approved agent_views objects"
                )
            continue

        object_name = identifiers[0]
        if object_name not in AGENT_VIEW_NAMES and object_name not in cte_names:
            raise ValueError(
                "Queries may access only approved agent view objects"
            )


def _validate_readonly_sql(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty SQL string")

    normalized = query.strip()
    without_trailing_semicolon = normalized[:-1].strip() if normalized.endswith(";") else normalized

    if ";" in without_trailing_semicolon:
        raise ValueError("Only one SQL statement is allowed")
    if SQL_COMMENT_RE.search(without_trailing_semicolon):
        raise ValueError("SQL comments are not allowed")
    if not READONLY_SQL_START_RE.match(without_trailing_semicolon):
        raise ValueError("Only SELECT or WITH queries are allowed")
    if BLOCKED_SQL_RE.search(without_trailing_semicolon):
        raise ValueError("Query contains a blocked SQL keyword")
    _validate_view_relations(without_trailing_semicolon)

    return without_trailing_semicolon


def get_db_info(
    *,
    db: Session,
    engine: Engine,
    include_row_counts: bool = True,
    max_tables: int = 50,
) -> DatabaseInfo:
    """
    Return metadata and optional row counts for approved agent views.

    This helper is intentionally fixed to AGENT_VIEW_SCHEMA so callers cannot
    accidentally expose base tables or internal application schemas.
    """
    inspector = inspect(engine)
    dialect = engine.dialect.name
    schema = AGENT_VIEW_SCHEMA
    object_names = inspector.get_view_names(schema=schema)
    object_names = sorted(object_names)[:max_tables]

    out_tables: list[TableInfo] = []

    for t in object_names:
        if t in SENSITIVE_TABLES:
            continue

        cols = []
        for c in inspector.get_columns(t, schema=schema):
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

        fks = []
        idxs = []

        row_count = None
        if include_row_counts:
            # Row count is safe and very useful for agent planning
            quoted_schema = engine.dialect.identifier_preparer.quote_schema(schema)
            quoted_name = engine.dialect.identifier_preparer.quote(t)
            row_count = db.execute(
                text(f"SELECT COUNT(*) FROM {quoted_schema}.{quoted_name}")
            ).scalar_one()

        out_tables.append(
            TableInfo(
                name=t,
                columns=cols,
                primary_key=[],
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
            "scope": f"{schema} views only. Base tables and internal schemas are hidden.",
        },
    )



@tool
def get_db_info_tool(include_row_counts: bool = False) -> dict:
    """View schema metadata and optional row counts through a read-only connection."""
    with ReadOnlySessionLocal() as db:
        return get_db_info(
            db=db,
            engine=readonly_engine,
            include_row_counts=include_row_counts,
        ).model_dump()


def get_sql_database_toolkit_tools(llm):
    """Return non-executing SQL tools backed by the agent read-only engine."""
    sql_db = SQLDatabase(
        engine=readonly_engine,
        schema=AGENT_VIEW_SCHEMA,
        sample_rows_in_table_info=0,
        indexes_in_table_info=True,
        view_support=True,
        lazy_table_reflection=True,
    )
    toolkit = SQLDatabaseToolkit(db=sql_db, llm=llm)
    return [tool for tool in toolkit.get_tools() if tool.name != "sql_db_query"]


def run_readonly_sql(query: str, max_rows: int = 100) -> dict:
    safe_query = _validate_readonly_sql(query)
    safe_max_rows = max(1, min(int(max_rows or 100), MAX_SQL_ROWS))

    with readonly_engine.connect() as conn:
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


@tool
def run_readonly_sql_tool(query: str, max_rows: int = 100) -> dict:
    """
    Execute one guarded SELECT/WITH query through the agent read-only connection.

    Write/DDL statements are rejected before reaching a PostgreSQL transaction
    that is also forced to READ ONLY.
    """
    return run_readonly_sql(query, max_rows)
