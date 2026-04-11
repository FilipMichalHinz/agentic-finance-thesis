from typing import Optional, Dict

from src.integrations.supabase_client import get_supabase_client


def get_latest_price_before(
    ticker: str,
    as_of: str,
) -> Optional[Dict]:
    """
    Return the most recent daily price snapshot at or before the given timestamp.
    """
    supabase = get_supabase_client()
    res = (
        supabase.table("market_prices_daily")
        .select("event_timestamp, price_open, price_high, price_low, price_close, volume")
        .eq("ticker", ticker)
        .lte("event_timestamp", as_of)
        .order("event_timestamp", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None
