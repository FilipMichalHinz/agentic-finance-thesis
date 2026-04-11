from datetime import date, datetime, timezone
from typing import Dict, Optional

from src.integrations.supabase_client import get_supabase_client


def _parse_as_of_date(as_of: str) -> date:
    text = as_of.strip()
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


def get_latest_technical_indicators(
    ticker: str,
    as_of: str,
) -> Dict:
    """
    Return the latest stored technical indicators for a ticker on or before as_of.

    The payload is kept small so it is easy for the agent to read directly.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must be a non-empty string")

    as_of_date = _parse_as_of_date(as_of)
    supabase = get_supabase_client()
    response = (
        supabase.table("technical_indicators_daily")
        .select("ticker,event_date,sma,ema,wma,dema,tema,rsi,standarddeviation,williams,adx")
        .eq("ticker", normalized_ticker)
        .lte("event_date", as_of_date.isoformat())
        .order("event_date", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []

    if not rows:
        return {
            "ticker": normalized_ticker,
            "as_of": as_of_date.isoformat(),
            "event_date": None,
            "data_available": False,
            "sma": None,
            "ema": None,
            "wma": None,
            "dema": None,
            "tema": None,
            "rsi": None,
            "standarddeviation": None,
            "williams": None,
            "adx": None,
        }

    row = rows[0]
    return {
        "ticker": row.get("ticker", normalized_ticker),
        "as_of": as_of_date.isoformat(),
        "event_date": row.get("event_date"),
        "data_available": True,
        "sma": row.get("sma"),
        "ema": row.get("ema"),
        "wma": row.get("wma"),
        "dema": row.get("dema"),
        "tema": row.get("tema"),
        "rsi": row.get("rsi"),
        "standarddeviation": row.get("standarddeviation"),
        "williams": row.get("williams"),
        "adx": row.get("adx"),
    }
