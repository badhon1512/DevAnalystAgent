from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.admin import require_admin
from app.deps import get_db
from app.schemas.page_views import PageViewCreate, PageViewRecorded, PageViewStats
from app.services.page_views import page_view_stats, record_page_view

router = APIRouter(prefix="/page-views", tags=["page-views"])


@router.post("", response_model=PageViewRecorded)
def track_page_view(
    payload: PageViewCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> PageViewRecorded:
    """Public beacon endpoint. Deliberately unauthenticated and always 200.

    Analytics must never break the page it measures, so a request that is
    ignored (a bot, for instance) still returns a successful response.
    """
    headers = {key.lower(): value for key, value in request.headers.items()}
    view = record_page_view(
        db,
        path=payload.path,
        referrer=payload.referrer,
        session_id=payload.session_id,
        user_agent=headers.get("user-agent"),
        headers=headers,
        fallback_ip=request.client.host if request.client else None,
    )
    return PageViewRecorded(recorded=view is not None)


@router.get("/stats", response_model=PageViewStats, dependencies=[Depends(require_admin)])
def page_view_statistics(
    days: int = Query(default=30, ge=1, le=365),
    path: str | None = Query(default=None, max_length=300),
    db: Session = Depends(get_db),
) -> PageViewStats:
    """Admin-only traffic summary for a trailing window."""
    return page_view_stats(db, days=days, path=path)
