from pathlib import Path
import sys
from typing import Literal

from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

from app.db.readonly_session import (
    ReadOnlySessionLocal,
    readonly_engine,
)
from app.db.session import SessionLocal
from app.rag.constants import DEFAULT_RETRIEVAL_TOP_K, MAX_RETRIEVAL_TOP_K
from app.rag.retriever import search_company_docs
from app.tools.db import get_db_info, run_readonly_sql

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

mcp = FastMCP("TraceStock AI")

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
    Inspect approved commerce views and optional row counts.

    Use this before writing SQL for product, inventory, sales, returns, warehouse,
    review, competitor, or market analysis.
    """
    with ReadOnlySessionLocal() as db:
        return get_db_info(
            db=db,
            engine=readonly_engine,
            include_row_counts=include_row_counts,
        ).model_dump()


@mcp.tool()
def run_readonly_inventory_sql(query: str, max_rows: int = 100) -> dict:
    """
    Execute one guarded read-only SELECT/WITH query against the TraceStock database.

    Write operations and DDL are blocked by the underlying database tool.
    """
    return run_readonly_sql(query, max_rows)


@mcp.tool()
def search_company_documents(
    query: str,
    top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    retrieval_mode: Literal["vector", "keyword", "hybrid"] = "hybrid",
) -> dict:
    """
    Search indexed company policies, SOPs, supplier rules, return policies, and warehouse docs.

    Use this for unstructured company knowledge rather than live product/inventory/sales facts.
    """
    safe_top_k = max(
        1,
        min(int(top_k or DEFAULT_RETRIEVAL_TOP_K), MAX_RETRIEVAL_TOP_K),
    )
    with SessionLocal() as db:
        try:
            return search_company_docs(
                db=db,
                query=query,
                top_k=safe_top_k,
                retrieval_mode=retrieval_mode,
            ).model_dump()
        except Exception as exc:
            if retrieval_mode == "keyword":
                raise
            print(
                f"[MCP SERVER] {retrieval_mode} search failed, using keyword: {exc!r}",
                file=sys.stderr,
            )
            return search_company_docs(
                db=db,
                query=query,
                top_k=safe_top_k,
                retrieval_mode="keyword",
            ).model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
