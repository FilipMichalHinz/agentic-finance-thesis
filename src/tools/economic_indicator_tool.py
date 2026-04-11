from typing import Dict

from langchain_core.tools import tool

from src.integrations.economic_indicators import get_latest_economic_indicators_snapshot


def make_get_latest_economic_indicators_tool(as_of: str):
    """
    Create an economic-indicator tool for one fixed analysis date.

    The model does not supply dates directly. The point-in-time boundary is set
    by the workflow so macro retrieval stays consistent with the rest of the
    deep-analysis toolset.
    """

    @tool("get_latest_economic_indicators")
    def get_latest_economic_indicators() -> Dict[str, object]:
        """
        Fetch the latest US economic indicator observations at or before the
        fixed analysis date.
        """
        return get_latest_economic_indicators_snapshot(as_of=as_of)

    return get_latest_economic_indicators
