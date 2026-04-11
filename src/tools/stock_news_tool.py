from typing import Dict, List, Optional

from langchain_core.tools import tool

from src.integrations.stock_news import retrieve_stock_news_for_date


def make_retrieve_stock_news_tool(
    as_of: str,
    *,
    simulation_mode: Optional[str] = None,
    disinformation_policy: Optional[str] = None,
):
    """
    Create a stock-news tool for one fixed analysis date.

    The model only supplies the ticker. The point-in-time date and runtime
    context are fixed outside the tool so retrieval stays predictable and the
    tool surface remains neutral.
    """

    @tool("retrieve_stock_news")
    def retrieve_stock_news(ticker: str) -> List[Dict[str, Optional[str]]]:
        """
        Return stock-specific news rows for the ticker on the fixed analysis date.
        Each row contains title, content, publisher, and site.
        """
        return retrieve_stock_news_for_date(
            ticker=ticker,
            as_of=as_of,
            simulation_mode=simulation_mode,
            disinformation_policy=disinformation_policy,
        )

    return retrieve_stock_news
