from pathlib import Path
import os
import re
import sys
from decimal import Decimal
from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP
from sqlalchemy import inspect, text

from app.db.session import SessionLocal, engine
from app.rag.retriever import search_company_docs

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

mcp = FastMCP("TraceStock AI")

MAX_SQL_ROWS = 200
VECTOR_DOCUMENT_SEARCH_AVAILABLE = os.getenv("MCP_VECTOR_DOCUMENT_SEARCH", "0") == "1"
READONLY_SQL_START_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
BLOCKED_SQL_RE = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|truncate|merge|grant|revoke|"
    r"copy|call|execute|do|vacuum|analyze|refresh|lock|set|reset"
    r")\b",
    re.IGNORECASE,
)
SENSITIVE_COLUMNS = {
    "email",
    "phone",
    "address",
    "customer_name",
    "first_name",
    "last_name",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _should_hide_column(column_name: str) -> bool:
    return column_name.lower() in SENSITIVE_COLUMNS


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


def _fallback_document_keyword_search(db: Any, query: str, top_k: int) -> dict:
    words = [
        word.lower()
        for word in re.findall(r"[a-zA-Z0-9]+", query)
        if len(word) > 2
    ][:6]
    if not words:
        words = [query.strip().lower()]

    params: dict[str, Any] = {"top_k": top_k}
    conditions = []
    for index, word in enumerate(words):
        param_name = f"term_{index}"
        params[param_name] = f"%{word}%"
        conditions.append(
            f"(lower(c.content) LIKE :{param_name} OR lower(d.title) LIKE :{param_name})"
        )

    rows = db.execute(
        text(
            f"""
            SELECT
                d.document_id,
                c.chunk_id,
                d.title,
                c.content,
                d.source_type,
                d.source_path,
                d.department,
                d.version,
                c.chunk_index
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            WHERE {" OR ".join(conditions)}
            ORDER BY d.title, c.chunk_index
            LIMIT :top_k
            """
        ),
        params,
    ).mappings()

    return {
        "query": query,
        "retrieval_mode": "keyword_fallback",
        "matches": [
            {
                "document_id": str(row["document_id"]),
                "chunk_id": str(row["chunk_id"]),
                "title": row["title"],
                "content": row["content"],
                "score": 0.0,
                "source_type": row["source_type"],
                "source_path": row["source_path"],
                "department": row["department"],
                "version": row["version"],
                "chunk_index": row["chunk_index"],
            }
            for row in rows
        ],
    }


@mcp.tool()
def tracestock_mcp_status() -> dict:
    """Return a small status payload proving the TraceStock MCP server is reachable."""
    return {
        "name": "TraceStock AI MCP",
        "status": "ready",
        "tools": [
            "get_inventory_schema",
            "run_readonly_inventory_sql",
            "search_company_documents",
            "get_weather_forecast",
        ],
    }


def _weather_units(units: str) -> dict[str, str]:
    if units == "imperial":
        return {
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
    return {
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }


def _parse_weather_location(location: str) -> tuple[str, str | None]:
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if len(parts) < 2:
        return location.strip(), None

    country = parts[-1].upper()
    query = ", ".join(parts[:-1]).strip()
    if len(country) == 2 and country.isalpha() and query:
        return query, country
    return location.strip(), None


@mcp.tool()
def get_weather_forecast(location: str, days: int = 7, units: str = "metric") -> dict:
    """
    Return current and daily weather forecast for a city/location.

    Use this for weather-aware demand analysis, branch planning, seasonal product recommendations,
    and customer questions involving rain, heat, cold, UV, or wind.
    """
    if not isinstance(location, str) or not location.strip():
        raise ValueError("location must be a non-empty string")

    safe_days = max(1, min(int(days or 7), 16))
    safe_units = "imperial" if units == "imperial" else "metric"
    unit_params = _weather_units(safe_units)
    location_query, country_code = _parse_weather_location(location)
    geocoding_params = {
        "name": location_query,
        "count": 1,
        "language": "en",
        "format": "json",
    }
    if country_code:
        geocoding_params["countryCode"] = country_code

    with httpx.Client(timeout=20.0) as client:
        geo_response = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params=geocoding_params,
        )
        geo_response.raise_for_status()
        geo_payload = geo_response.json()
        results = geo_payload.get("results") or []
        if not results:
            return {"location": location, "error": "Location not found"}

        place = results[0]
        forecast_response = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,uv_index_max",
                "forecast_days": safe_days,
                "timezone": "auto",
                **unit_params,
            },
        )
        forecast_response.raise_for_status()
        forecast = forecast_response.json()

    daily = forecast.get("daily") or {}
    days_payload = []
    for index, forecast_date in enumerate(daily.get("time") or []):
        days_payload.append(
            {
                "date": forecast_date,
                "weather_code": (daily.get("weather_code") or [None])[index],
                "temperature_max": (daily.get("temperature_2m_max") or [None])[index],
                "temperature_min": (daily.get("temperature_2m_min") or [None])[index],
                "precipitation_sum": (daily.get("precipitation_sum") or [None])[index],
                "wind_speed_max": (daily.get("wind_speed_10m_max") or [None])[index],
                "uv_index_max": (daily.get("uv_index_max") or [None])[index],
            }
        )

    return {
        "requested_location": location,
        "resolved_location": {
            "name": place.get("name"),
            "admin1": place.get("admin1"),
            "country": place.get("country"),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
            "timezone": place.get("timezone"),
        },
        "units": {
            "system": safe_units,
            "temperature": forecast.get("current_units", {}).get("temperature_2m"),
            "precipitation": forecast.get("daily_units", {}).get("precipitation_sum"),
            "wind_speed": forecast.get("daily_units", {}).get("wind_speed_10m_max"),
        },
        "current": forecast.get("current"),
        "daily": days_payload,
        "demand_hints": {
            "heat_sensitive": "Air conditioners, sunscreen, hydration/travel products rise with high temperature or UV.",
            "cold_sensitive": "Space heaters and indoor comfort products rise with low temperature.",
            "rain_sensitive": "Rain jackets and waterproof footwear rise with precipitation forecasts.",
            "wind_sensitive": "Outdoor apparel and commute products may shift with high wind forecasts.",
        },
    }


@mcp.tool()
def get_inventory_schema(include_row_counts: bool = False) -> dict:
    """
    Inspect TraceStock database tables, columns, foreign keys, indexes, and optional row counts.

    Use this before writing SQL against the inventory, product, sales, returns, warehouse,
    conversation, or document tables.
    """
    inspector = inspect(engine)
    tables = []

    with SessionLocal() as db:
        for table_name in sorted(inspector.get_table_names(schema="public")):
            columns = []
            for column in inspector.get_columns(table_name, schema="public"):
                column_name = column.get("name", "")
                if _should_hide_column(column_name):
                    continue
                columns.append(
                    {
                        "name": column_name,
                        "type": str(column.get("type")),
                        "nullable": bool(column.get("nullable", True)),
                        "default": str(column.get("default"))
                        if column.get("default") is not None
                        else None,
                    }
                )

            primary_key = inspector.get_pk_constraint(table_name, schema="public") or {}
            foreign_keys = []
            for foreign_key in inspector.get_foreign_keys(table_name, schema="public") or []:
                constrained = foreign_key.get("constrained_columns") or []
                referred_columns = foreign_key.get("referred_columns") or []
                for index, column_name in enumerate(constrained):
                    if _should_hide_column(column_name):
                        continue
                    foreign_keys.append(
                        {
                            "column": column_name,
                            "references_table": foreign_key.get("referred_table") or "",
                            "references_column": referred_columns[index]
                            if index < len(referred_columns)
                            else "",
                        }
                    )

            row_count = None
            if include_row_counts:
                row_count = db.execute(text(f'SELECT COUNT(*) FROM public."{table_name}"')).scalar_one()

            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "primary_key": primary_key.get("constrained_columns") or [],
                    "foreign_keys": foreign_keys,
                    "row_count": row_count,
                }
            )

    return {
        "dialect": engine.dialect.name,
        "tables": tables,
        "notes": {
            "privacy": "No raw rows returned. Potential PII columns are filtered.",
            "scope": "public schema only.",
        },
    }


@mcp.tool()
def run_readonly_inventory_sql(query: str, max_rows: int = 100) -> dict:
    """
    Execute one guarded read-only SELECT/WITH query against the TraceStock database.

    Write operations and DDL are blocked by the underlying database tool.
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


@mcp.tool()
def search_company_documents(query: str, top_k: int = 5) -> dict:
    """
    Search indexed company policies, SOPs, supplier rules, return policies, and warehouse docs.

    Use this for unstructured company knowledge rather than live product/inventory/sales facts.
    """
    global VECTOR_DOCUMENT_SEARCH_AVAILABLE
    safe_top_k = max(1, min(int(top_k or 5), 20))
    with SessionLocal() as db:
        if not VECTOR_DOCUMENT_SEARCH_AVAILABLE:
            return _fallback_document_keyword_search(db, query, safe_top_k)

        try:
            return search_company_docs(db=db, query=query, top_k=safe_top_k).model_dump()
        except Exception as exc:
            VECTOR_DOCUMENT_SEARCH_AVAILABLE = False
            print(
                f"[MCP SERVER] vector document search failed, using keyword fallback: {exc!r}",
                file=sys.stderr,
            )
            return _fallback_document_keyword_search(db, query, safe_top_k)


if __name__ == "__main__":
    mcp.run(transport="stdio")
