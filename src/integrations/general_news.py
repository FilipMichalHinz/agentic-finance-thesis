from datetime import date, datetime, time, timezone
from typing import Dict, List, Optional

GENERAL_NEWS_SELECT_COLUMNS = "title,content,publisher,site,published_at"


def _parse_as_of_date(as_of: str) -> date:
    text = (as_of or "").strip()
    if not text:
        raise ValueError("as_of must be a non-empty ISO timestamp or YYYY-MM-DD date")

    candidate = text.replace("Z", "+00:00")
    try:
        dt_value = datetime.fromisoformat(candidate)
    except ValueError:
        dt_value = datetime.strptime(text, "%Y-%m-%d")

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc).date()


def _day_bounds(as_of_date: date) -> tuple[str, str]:
    day_start = datetime.combine(as_of_date, time.min, tzinfo=timezone.utc).isoformat()
    day_end = datetime.combine(as_of_date, time.max, tzinfo=timezone.utc).isoformat()
    return day_start, day_end


def _fetch_general_news_rows(day_start: str, day_end: str) -> List[Dict[str, Optional[str]]]:
    from src.integrations.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = (
        supabase.table("general_news_daily")
        .select(GENERAL_NEWS_SELECT_COLUMNS)
        .gte("published_at", day_start)
        .lte("published_at", day_end)
        .order("published_at", desc=True)
        .execute()
    )
    return response.data or []


def get_all_general_news_for_date(as_of: str) -> List[Dict[str, Optional[str]]]:
    """
    Return all general-news rows for the UTC trading date of as_of.
    """
    as_of_date = _parse_as_of_date(as_of)
    day_start, day_end = _day_bounds(as_of_date)
    rows = _fetch_general_news_rows(day_start, day_end)
    return [
        {
            "title": row.get("title"),
            "content": row.get("content"),
            "publisher": row.get("publisher"),
            "site": row.get("site"),
        }
        for row in rows
    ]
