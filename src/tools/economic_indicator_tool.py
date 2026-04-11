from typing import Dict

from langchain_core.tools import tool

from src.integrations.economic_indicators import get_latest_economic_indicators_snapshot


@tool("get_latest_economic_indicators")
def get_latest_economic_indicators(
    as_of: str,
) -> Dict[str, object]:
    """
    Fetch the latest US economic indicator observations at or before the trading day in as_of.
    """
    return get_latest_economic_indicators_snapshot(as_of=as_of)
