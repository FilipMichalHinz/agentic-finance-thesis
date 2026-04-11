from typing import Dict

from langchain_core.tools import tool

from src.integrations.financial_ratios import get_financial_ratios_history


def make_get_financial_ratios_tool(as_of: str):
    """
    Create a tool that reads annual financial ratios for one fixed analysis date.

    The model only supplies the ticker and optional year count. The date is fixed
    outside the tool so the point-in-time rule stays simple and predictable.
    """

    @tool("get_financial_ratios")
    def get_financial_ratios(ticker: str, years: int = 10) -> Dict:
        """
        Return annual financial ratios for a ticker using only filings available
        on or before the fixed analysis date.
        """
        return get_financial_ratios_history(
            ticker=ticker,
            as_of=as_of,
            years=years,
        )

    return get_financial_ratios
