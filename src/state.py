from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state for one baseline daily run.

    The baseline keeps one explicit state object so that the workflow remains easy
    to inspect. The state contains only current-run coordination data. Persistent
    history still belongs in Supabase.
    """

    run_id: str
    package_date: str
    requested_package_date: Optional[str]
    initial_cash: float
    simulation_mode: str
    disinformation_policy: str

    daily_packages: Dict[str, Dict[str, Any]]
    current_portfolio: Dict[str, Any]

    technical_screening: List[Dict[str, Any]]
    news_screening: List[Dict[str, Any]]
    fundamental_screening: List[Dict[str, Any]]

    shared_deep_analysis_set: List[str]

    technical_report: str
    news_report: str
    fundamental_report: str

    portfolio_decision: Dict[str, Any]
    trade_preview: Dict[str, Any]
    stored_decision: Dict[str, Any]

    messages: List[str]
