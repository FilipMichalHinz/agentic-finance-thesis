from datetime import date, datetime
from typing import Dict, Optional

from src.integrations.supabase_client import get_supabase_client

INDICATOR_NAMES = (
    "GDP",
    "CPI",
    "inflationRate",
    "unemploymentRate",
)

def _parse_as_of_date(as_of: str) -> str:
    value = (as_of or "").strip()
    if not value:
        raise ValueError("as_of is required")

    if "T" not in value:
        return date.fromisoformat(value).isoformat()

    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def get_latest_economic_indicators_snapshot(as_of: str) -> Dict[str, object]:
    """
    Return the latest US economic indicator values at or before the trading day in as_of.
    """
    supabase = get_supabase_client()
    cutoff_date = _parse_as_of_date(as_of)
    indicators: Dict[str, Optional[Dict[str, object]]] = {}

    for indicator_name in INDICATOR_NAMES:
        response = (
            supabase.table("economic_indicators")
            .select("indicator_name, event_date, value")
            .eq("country", "US")
            .eq("indicator_name", indicator_name)
            .lte("event_date", cutoff_date)
            .order("event_date", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        indicators[indicator_name] = rows[0] if rows else None

    return {
        "as_of_date": cutoff_date,
        "indicators": indicators,
    }
