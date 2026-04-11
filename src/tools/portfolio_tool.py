from typing import Any, Dict, Optional

from langchain_core.tools import tool

from src.integrations.portfolio_runtime import (
    get_portfolio_compliance_summary,
    get_portfolio_risk_summary,
)


@tool("get_portfolio_compliance_summary")
def get_portfolio_compliance_summary_tool(
    run_id: str,
    target_weights: Optional[Dict[str, Any]] = None,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check either the current portfolio or a proposed target allocation against the IPS.
    """
    return get_portfolio_compliance_summary(
        run_id=run_id,
        target_weights=target_weights,
        as_of=as_of,
    )


@tool("get_portfolio_risk_summary")
def get_portfolio_risk_summary_tool(
    run_id: str,
    lookback_days: int = 60,
) -> Dict[str, Any]:
    """
    Return concentration, volatility, and drawdown metrics for the current portfolio.
    """
    return get_portfolio_risk_summary(run_id=run_id, lookback_days=lookback_days)
