import os
from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Dict, List, Optional

STOCK_NEWS_SELECT_COLUMNS = "id,title,content,publisher,site,published_at"
SIMULATION_MODE_ENV_KEYS = (
    "NEWS_SIMULATION_MODE",
    "SIMULATION_MODE",
    "MANIPULATION_MODE",
)
DISINFORMATION_POLICY_ENV_KEYS = (
    "STOCK_NEWS_DISINFORMATION_POLICY",
    "NEWS_DISINFORMATION_POLICY",
)


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


def _normalize_simulation_mode(value: Optional[str]) -> str:
    text = (value or "").strip()
    if not text:
        return "clean"

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"clean", "baseline", "normal"}:
        return "clean"
    if normalized in {"disinformation", "disinfo", "disinformed", "manipulated", "manipulation"}:
        return "disinformation"
    raise ValueError(f"Unsupported simulation mode: {value}")


def resolve_stock_news_simulation_mode(simulation_mode: Optional[str] = None) -> str:
    if simulation_mode is not None:
        return _normalize_simulation_mode(simulation_mode)

    for env_key in SIMULATION_MODE_ENV_KEYS:
        env_value = os.getenv(env_key)
        if env_value is not None:
            return _normalize_simulation_mode(env_value)
    return "clean"


def _normalize_disinformation_policy(value: Optional[str]) -> str:
    text = (value or "").strip()
    if not text:
        return "append"

    normalized = text.lower().replace("-", "_").replace(" ", "_")
    if normalized in {"replace", "append"}:
        return normalized
    raise ValueError(f"Unsupported disinformation policy: {value}")


def resolve_stock_news_disinformation_policy(disinformation_policy: Optional[str] = None) -> str:
    if disinformation_policy is not None:
        return _normalize_disinformation_policy(disinformation_policy)

    for env_key in DISINFORMATION_POLICY_ENV_KEYS:
        env_value = os.getenv(env_key)
        if env_value is not None:
            return _normalize_disinformation_policy(env_value)
    return "append"


def _day_bounds(as_of_date: date) -> tuple[str, str]:
    day_start = datetime.combine(as_of_date, time.min, tzinfo=timezone.utc).isoformat()
    day_end = datetime.combine(as_of_date, time.max, tzinfo=timezone.utc).isoformat()
    return day_start, day_end


def _fetch_clean_stock_news_rows(
    ticker: str,
    day_start: str,
    day_end: str,
) -> List[Dict[str, Optional[str]]]:
    from src.integrations.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = (
        supabase.table("stock_news_daily")
        .select(STOCK_NEWS_SELECT_COLUMNS)
        .eq("ticker", ticker)
        .gte("published_at", day_start)
        .lte("published_at", day_end)
        .order("published_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_clean_stock_news_rows_for_day(
    day_start: str,
    day_end: str,
) -> List[Dict[str, Optional[str]]]:
    from src.integrations.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = (
        supabase.table("stock_news_daily")
        .select(f"ticker,{STOCK_NEWS_SELECT_COLUMNS}")
        .gte("published_at", day_start)
        .lte("published_at", day_end)
        .order("published_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_manipulated_stock_news_rows(
    ticker: str,
    day_start: str,
    day_end: str,
) -> List[Dict[str, Optional[str]]]:
    from src.integrations.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = (
        supabase.table("manipulated_stock_news_daily")
        .select(STOCK_NEWS_SELECT_COLUMNS)
        .eq("ticker", ticker)
        .gte("published_at", day_start)
        .lte("published_at", day_end)
        .order("published_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_manipulated_stock_news_rows_for_day(
    day_start: str,
    day_end: str,
) -> List[Dict[str, Optional[str]]]:
    from src.integrations.supabase_client import get_supabase_client

    supabase = get_supabase_client()
    response = (
        supabase.table("manipulated_stock_news_daily")
        .select(f"ticker,{STOCK_NEWS_SELECT_COLUMNS}")
        .gte("published_at", day_start)
        .lte("published_at", day_end)
        .order("published_at", desc=True)
        .execute()
    )
    return response.data or []


def _merge_stock_news_rows(
    clean_rows: List[Dict[str, Optional[str]]],
    manipulated_rows: List[Dict[str, Optional[str]]],
    disinformation_policy: str,
) -> List[Dict[str, Optional[str]]]:
    if not manipulated_rows:
        merged_rows = clean_rows
    elif disinformation_policy == "append":
        merged_rows = clean_rows + manipulated_rows
    else:
        # Manipulated rows are scheduled independently and are not currently
        # linked to one exact clean row, so "replace" means use the day-level
        # manipulated set whenever one exists for that ticker/date.
        merged_rows = manipulated_rows

    return sorted(
        merged_rows,
        key=lambda row: row.get("published_at") or "",
        reverse=True,
    )


def _format_stock_news_rows(rows: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    return [
        {
            "title": row.get("title"),
            "content": row.get("content"),
            "publisher": row.get("publisher"),
            "site": row.get("site"),
        }
        for row in rows
    ]


def _group_rows_by_ticker(rows: List[Dict[str, Optional[str]]]) -> Dict[str, List[Dict[str, Optional[str]]]]:
    grouped: Dict[str, List[Dict[str, Optional[str]]]] = defaultdict(list)
    for row in rows:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        grouped[ticker].append(row)
    return grouped


def build_daily_news_package_fields_for_date(
    as_of: str,
    *,
    simulation_mode: Optional[str] = None,
    disinformation_policy: Optional[str] = None,
) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Return agent-facing stock-news package fields for one trading day.

    The returned mapping is keyed by ticker and always exposes a neutral schema:
    latest_news_id, latest_news_title, daily_news_count. In disinformation mode
    the values come from the merged clean/manipulated day-level news set, but
    the calling code never needs to know which source produced the latest item.
    """

    as_of_date = _parse_as_of_date(as_of)
    day_start, day_end = _day_bounds(as_of_date)
    active_simulation_mode = resolve_stock_news_simulation_mode(simulation_mode)
    active_disinformation_policy = resolve_stock_news_disinformation_policy(disinformation_policy)

    clean_rows = _fetch_clean_stock_news_rows_for_day(day_start, day_end)
    clean_by_ticker = _group_rows_by_ticker(clean_rows)

    manipulated_by_ticker: Dict[str, List[Dict[str, Optional[str]]]] = {}
    if active_simulation_mode == "disinformation":
        manipulated_rows = _fetch_manipulated_stock_news_rows_for_day(day_start, day_end)
        manipulated_by_ticker = _group_rows_by_ticker(manipulated_rows)

    package_fields: Dict[str, Dict[str, Optional[str]]] = {}
    all_tickers = set(clean_by_ticker.keys()) | set(manipulated_by_ticker.keys())
    for ticker in all_tickers:
        merged_rows = _merge_stock_news_rows(
            clean_rows=clean_by_ticker.get(ticker, []),
            manipulated_rows=manipulated_by_ticker.get(ticker, []),
            disinformation_policy=active_disinformation_policy,
        )
        latest_row = merged_rows[0] if merged_rows else None
        package_fields[ticker] = {
            "latest_news_id": latest_row.get("id") if latest_row else None,
            "latest_news_title": latest_row.get("title") if latest_row else None,
            "daily_news_count": len(merged_rows),
        }

    return package_fields


def retrieve_stock_news_for_date(
    ticker: str,
    as_of: str,
    *,
    simulation_mode: Optional[str] = None,
    disinformation_policy: Optional[str] = None,
) -> List[Dict[str, Optional[str]]]:
    """
    Return stock-specific news rows for one ticker on the UTC trading date of as_of.

    In clean mode the tool returns rows from stock_news_daily only. In
    disinformation mode it appends manipulated rows by default, but can also
    replace the day-level clean set when requested.
    """
    normalized_ticker = (ticker or "").strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must be a non-empty string")

    as_of_date = _parse_as_of_date(as_of)
    day_start, day_end = _day_bounds(as_of_date)
    active_simulation_mode = resolve_stock_news_simulation_mode(simulation_mode)

    clean_rows = _fetch_clean_stock_news_rows(
        ticker=normalized_ticker,
        day_start=day_start,
        day_end=day_end,
    )
    if active_simulation_mode == "clean":
        return _format_stock_news_rows(clean_rows)

    manipulated_rows = _fetch_manipulated_stock_news_rows(
        ticker=normalized_ticker,
        day_start=day_start,
        day_end=day_end,
    )
    active_disinformation_policy = resolve_stock_news_disinformation_policy(disinformation_policy)
    merged_rows = _merge_stock_news_rows(
        clean_rows=clean_rows,
        manipulated_rows=manipulated_rows,
        disinformation_policy=active_disinformation_policy,
    )
    return _format_stock_news_rows(merged_rows)
