from datetime import datetime

from pydantic import BaseModel, Field


class PageViewCreate(BaseModel):
    path: str = Field(default="/", max_length=300)
    referrer: str | None = Field(default=None, max_length=500)
    session_id: str | None = Field(default=None, max_length=64)


class PageViewRecorded(BaseModel):
    recorded: bool


class CountBucket(BaseModel):
    label: str
    views: int


class DailyViews(BaseModel):
    date: str
    views: int
    visitors: int


class RecentView(BaseModel):
    viewed_at: datetime
    path: str
    country: str | None = None
    city: str | None = None
    referrer: str | None = None


class PageViewStats(BaseModel):
    generated_at: str
    window_days: int
    total_views: int
    unique_visitors: int
    views_today: int
    daily: list[DailyViews]
    top_countries: list[CountBucket]
    top_paths: list[CountBucket]
    top_referrers: list[CountBucket]
    recent: list[RecentView]
