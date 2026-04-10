import os
from typing import Optional, Dict

from dotenv import load_dotenv
from supabase import create_client, Client

_SUPABASE_CLIENT: Optional[Client] = None


def _get_supabase_client() -> Client:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT


def get_latest_price_before(
    ticker: str,
    as_of: str,
) -> Optional[Dict]:
    """
    Return the most recent daily price snapshot at or before the given timestamp.
    """
    supabase = _get_supabase_client()
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
