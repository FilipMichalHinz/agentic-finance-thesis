from typing import Dict, Optional

from langchain_core.tools import tool

from src.integrations.market_prices import get_latest_price_before


@tool("get_price_snapshot")
def get_price_snapshot(
    ticker: str,
    as_of: str,
) -> Optional[Dict]:
    """
    Fetch the latest hourly OHLCV price snapshot at or before the given timestamp.
    """
    return get_latest_price_before(ticker=ticker, as_of=as_of)
