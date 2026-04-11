from typing import Dict

from langchain_core.tools import tool

from src.integrations.technical_indicators import get_latest_technical_indicators


def make_get_technical_indicators_tool(as_of: str):
    """
    Create a tool that reads technical indicators for one fixed analysis date.

    The model only supplies the ticker. The date is fixed outside the tool so
    the retrieval rule stays simple and predictable.
    """

    @tool("get_technical_indicators")
    def get_technical_indicators(ticker: str) -> Dict:
        """
        Return the current indicator snapshot together with 7, 30, and 90 day
        lookback snapshots for the same ticker.
        """
        return get_latest_technical_indicators(ticker=ticker, as_of=as_of)

    return get_technical_indicators
