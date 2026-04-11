from typing import Dict

from langchain_core.tools import tool

from src.integrations.technical_indicators import get_latest_technical_indicators


def make_get_technical_indicators_tool(as_of: str):
    """
    Create a tool that reads technical indicators for one fixed analysis date.

    The model only supplies the ticker. The workflow decides the date outside
    the tool, which keeps the retrieval rules explicit.
    """

    @tool("get_technical_indicators")
    def get_technical_indicators(ticker: str) -> Dict:
        """
        Return the latest stored technical indicators for a ticker.
        """
        return get_latest_technical_indicators(ticker=ticker, as_of=as_of)

    return get_technical_indicators
