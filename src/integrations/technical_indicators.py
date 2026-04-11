from datetime import date, datetime, timedelta, timezone
from typing import Dict

from src.integrations.supabase_client import get_supabase_client


INDICATOR_FIELDS = (
    "sma",
    "ema",
    "wma",
    "dema",
    "tema",
    "rsi",
    "standarddeviation",
    "williams",
    "adx",
)


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


def _empty_snapshot() -> Dict:
    snapshot = {
        "event_date": None,
        "data_available": False,
    }
    for field in INDICATOR_FIELDS:
        snapshot[field] = None
    return snapshot


def _get_snapshot_on_or_before(ticker: str, cutoff_date: date) -> Dict:
    """
    Return one compact indicator snapshot for the latest row at or before cutoff_date.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("technical_indicators_daily")
        .select("event_date,sma,ema,wma,dema,tema,rsi,standarddeviation,williams,adx")
        .eq("ticker", ticker)
        .lte("event_date", cutoff_date.isoformat())
        .order("event_date", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return _empty_snapshot()

    row = rows[0]
    snapshot = {
        "event_date": row.get("event_date"),
        "data_available": True,
    }
    for field in INDICATOR_FIELDS:
        snapshot[field] = row.get(field)
    return snapshot


def get_latest_technical_indicators(
    ticker: str,
    as_of: str,
) -> Dict:
    """
    Return the current indicator snapshot plus fixed lookback snapshots.

    Each lookback uses the latest row on or before the target date so missing
    market days do not break the output.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must be a non-empty string")

    as_of_date = _parse_as_of_date(as_of)
    return {
        "ticker": normalized_ticker,
        "as_of": as_of_date.isoformat(),
        "current": _get_snapshot_on_or_before(normalized_ticker, as_of_date),
        "lookback_7d": _get_snapshot_on_or_before(normalized_ticker, as_of_date - timedelta(days=7)),
        "lookback_30d": _get_snapshot_on_or_before(normalized_ticker, as_of_date - timedelta(days=30)),
        "lookback_90d": _get_snapshot_on_or_before(normalized_ticker, as_of_date - timedelta(days=90)),
    }
