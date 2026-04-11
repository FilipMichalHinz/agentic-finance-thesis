from typing import Dict, Optional

from langchain_core.tools import tool

from src.integrations.market_prices import get_latest_price_before


def make_get_price_snapshot_tool(as_of: str):
    """
    Create a price-snapshot tool for one fixed analysis date.

    The model only supplies the ticker. The point-in-time date is fixed outside
    the tool so analysts cannot accidentally request future data during deep
    analysis.
    """

    @tool("get_price_snapshot")
    def get_price_snapshot(ticker: str) -> Optional[Dict]:
        """
        Fetch the latest daily OHLCV price snapshot at or before the fixed
        analysis date.
        """
        return get_latest_price_before(ticker=ticker, as_of=as_of)

    return get_price_snapshot
