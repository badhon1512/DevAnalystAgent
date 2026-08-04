"""Recording and aggregation for public page views.

Design notes:
- The raw IP address is never persisted. It is salted and hashed, which still
  allows distinct visitors to be counted but keeps stored rows non-identifying.
- Location is taken from CDN headers when the platform provides them, which
  costs nothing. Only when they are absent, and only if explicitly enabled, is
  an external lookup attempted, and a failure there is never fatal.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import PageView
from app.schemas.page_views import (
    CountBucket,
    DailyViews,
    PageViewStats,
    RecentView,
)

GEO_LOOKUP_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city"
GEO_LOOKUP_TIMEOUT_SECONDS = 2.0

# Header names used by common proxies and CDNs, in preference order.
_COUNTRY_CODE_HEADERS = ("cf-ipcountry", "x-vercel-ip-country", "x-geo-country")
_CITY_HEADERS = ("cf-ipcity", "x-vercel-ip-city", "x-geo-city")

_BOT_MARKERS = ("bot", "crawler", "spider", "crawling", "headlesschrome", "curl/", "wget/")


def _visitor_salt() -> str:
    return os.getenv("PAGEVIEW_IP_SALT", "dev-pageview-salt")


def _geo_lookup_enabled() -> bool:
    return os.getenv("PAGEVIEW_GEO_LOOKUP", "0").strip().lower() in {"1", "true", "yes"}


def client_ip(headers: dict[str, str], fallback: str | None) -> str | None:
    """Resolve the originating client IP behind a proxy.

    Railway, Fly and most CDNs terminate TLS upstream, so request.client.host is
    the proxy rather than the visitor. X-Forwarded-For holds the original client
    as its first entry.
    """
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return headers.get("x-real-ip") or fallback


def hash_visitor(ip: str | None) -> str | None:
    if not ip:
        return None
    digest = hashlib.sha256(f"{_visitor_salt()}:{ip}".encode("utf-8"))
    return digest.hexdigest()


def is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    lowered = user_agent.lower()
    return any(marker in lowered for marker in _BOT_MARKERS)


@lru_cache(maxsize=2048)
def _lookup_location(ip: str) -> tuple[str | None, str | None, str | None]:
    """Best-effort IP geolocation. Cached, and never raises."""
    try:
        request = urllib.request.Request(
            GEO_LOOKUP_URL.format(ip=ip),
            headers={"User-Agent": "productai-pageviews"},
        )
        with urllib.request.urlopen(request, timeout=GEO_LOOKUP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None, None, None

    if payload.get("status") != "success":
        return None, None, None
    return payload.get("country"), payload.get("countryCode"), payload.get("city")


def resolve_location(
    headers: dict[str, str],
    ip: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Return (country, country_code, city) from headers, else optional lookup."""
    country_code = next(
        (headers[name] for name in _COUNTRY_CODE_HEADERS if headers.get(name)),
        None,
    )
    city = next((headers[name] for name in _CITY_HEADERS if headers.get(name)), None)

    if country_code and country_code.upper() not in {"XX", "T1"}:
        return None, country_code.upper()[:2], city

    if ip and _geo_lookup_enabled():
        return _lookup_location(ip)

    return None, None, city


def record_page_view(
    db: Session,
    *,
    path: str,
    referrer: str | None,
    session_id: str | None,
    user_agent: str | None,
    headers: dict[str, str],
    fallback_ip: str | None,
) -> PageView | None:
    """Persist one view. Returns None when the request is ignored as a bot."""
    if is_bot(user_agent):
        return None

    ip = client_ip(headers, fallback_ip)
    country, country_code, city = resolve_location(headers, ip)

    view = PageView(
        path=path[:300],
        session_id=session_id[:64] if session_id else None,
        visitor_hash=hash_visitor(ip),
        country=country[:80] if country else None,
        country_code=country_code[:2] if country_code else None,
        city=city[:120] if city else None,
        referrer=referrer[:500] if referrer else None,
        user_agent=user_agent[:400] if user_agent else None,
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


def _bucket(rows, *, fallback: str) -> list[CountBucket]:
    return [
        CountBucket(label=row.label or fallback, views=int(row.views or 0))
        for row in rows
    ]


def page_view_stats(db: Session, *, days: int = 30, path: str | None = None) -> PageViewStats:
    """Aggregate views over a trailing window, optionally scoped to one path."""
    now = datetime.utcnow()
    window_start = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def scoped(statement):
        statement = statement.where(PageView.created_at >= window_start)
        if path:
            statement = statement.where(PageView.path == path)
        return statement

    total_views = int(db.scalar(scoped(select(func.count()).select_from(PageView))) or 0)
    unique_visitors = int(
        db.scalar(scoped(select(func.count(func.distinct(PageView.visitor_hash))))) or 0
    )

    today_statement = select(func.count()).select_from(PageView).where(
        PageView.created_at >= today_start
    )
    if path:
        today_statement = today_statement.where(PageView.path == path)
    views_today = int(db.scalar(today_statement) or 0)

    daily_rows = db.execute(
        scoped(
            select(
                func.date_trunc("day", PageView.created_at).label("day"),
                func.count().label("views"),
                func.count(func.distinct(PageView.visitor_hash)).label("visitors"),
            )
        )
        .group_by("day")
        .order_by("day")
    ).all()
    daily = [
        DailyViews(
            date=row.day.strftime("%Y-%m-%d"),
            views=int(row.views or 0),
            visitors=int(row.visitors or 0),
        )
        for row in daily_rows
    ]

    country_rows = db.execute(
        scoped(
            select(
                func.coalesce(PageView.country, PageView.country_code).label("label"),
                func.count().label("views"),
            )
        )
        .group_by("label")
        .order_by(desc("views"))
        .limit(8)
    ).all()

    path_rows = db.execute(
        scoped(select(PageView.path.label("label"), func.count().label("views")))
        .group_by("label")
        .order_by(desc("views"))
        .limit(8)
    ).all()

    referrer_rows = db.execute(
        scoped(
            select(
                func.coalesce(PageView.referrer, "Direct").label("label"),
                func.count().label("views"),
            )
        )
        .group_by("label")
        .order_by(desc("views"))
        .limit(8)
    ).all()

    recent_rows = db.execute(
        scoped(select(PageView)).order_by(desc(PageView.created_at)).limit(25)
    ).scalars().all()

    return PageViewStats(
        generated_at=datetime.now(timezone.utc).isoformat(),
        window_days=days,
        total_views=total_views,
        unique_visitors=unique_visitors,
        views_today=views_today,
        daily=daily,
        top_countries=_bucket(country_rows, fallback="Unknown"),
        top_paths=_bucket(path_rows, fallback="/"),
        top_referrers=_bucket(referrer_rows, fallback="Direct"),
        recent=[
            RecentView(
                viewed_at=row.created_at,
                path=row.path,
                country=row.country or row.country_code,
                city=row.city,
                referrer=row.referrer,
            )
            for row in recent_rows
        ],
    )
