from typing import Dict, List, Optional

from langchain_core.tools import tool

from src.integrations.general_news import get_all_general_news_for_date


def make_get_all_general_news_tool(as_of: str):
    """
    Create a general-news tool for one fixed analysis date.

    The model does not supply the date, so retrieval stays bounded to the
    current runtime day.
    """

    @tool("get_all_general_news")
    def get_all_general_news() -> List[Dict[str, Optional[str]]]:
        """
        Return all general-news rows for the fixed analysis date.
        Each row contains title, content, publisher, and site.
        """
        return get_all_general_news_for_date(as_of=as_of)

    return get_all_general_news
