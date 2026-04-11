"""Simple baseline workflow graph.

This graph follows the artifact-spec baseline:
1. load prepared daily packages and current portfolio state
2. run specialist screening
3. build one shared deep-analysis set
4. run bounded analyst deep-analysis reports
5. let the Portfolio Manager produce one target portfolio
6. translate the target into an action-ready simulated rebalance preview
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.agents.cio import portfolio_manager_node
from src.agents.fundamental_analyst import fundamental_deep_analysis_node, fundamental_screen_node
from src.agents.sentiment_analyst import news_deep_analysis_node, news_screen_node
from src.agents.technical_analyst import technical_deep_analysis_node, technical_screen_node
from src.baseline_workflow import (
    build_shared_deep_analysis_set,
    extract_current_holdings,
    load_or_initialize_portfolio_state,
    resolve_package_date,
)
from src.integrations.daily_info_packages import load_all_daily_agent_packages
from src.integrations.portfolio_runtime import preview_rebalance
from src.integrations.portfolio_store import record_portfolio_decision
from src.state import AgentState


def load_baseline_inputs_node(state: AgentState):
    package_date = resolve_package_date(state.get("requested_package_date"))
    current_portfolio = load_or_initialize_portfolio_state(
        run_id=state["run_id"],
        package_date=package_date,
        initial_cash=state.get("initial_cash", 100000.0),
    )
    daily_packages = load_all_daily_agent_packages(
        package_date,
        simulation_mode=state.get("simulation_mode", "clean"),
        disinformation_policy=state.get("disinformation_policy", "append"),
    )
    return {
        "package_date": package_date,
        "daily_packages": daily_packages,
        "current_portfolio": current_portfolio,
    }


def build_shared_deep_analysis_set_node(state: AgentState):
    holdings = extract_current_holdings(state.get("current_portfolio"))
    deep_set = build_shared_deep_analysis_set(
        holdings=holdings,
        screening_outputs=[
            state.get("technical_screening", []),
            state.get("news_screening", []),
            state.get("fundamental_screening", []),
        ],
    )
    return {"shared_deep_analysis_set": deep_set}


def build_trade_preview_node(state: AgentState):
    decision = state["portfolio_decision"]
    preview = preview_rebalance(
        run_id=state["run_id"],
        as_of=state["package_date"],
        target_weights=decision["target_weights"],
        rationale=decision["summary"],
    )
    stored_decision = record_portfolio_decision(
        run_id=state["run_id"],
        decision_date=state["package_date"],
        execution_date=state["package_date"],
        target_weights=decision["target_weights"],
        action_plan=preview["actions"],
        rationale=decision["summary"],
        analyst_inputs={
            "technical_report": state.get("technical_report", ""),
            "news_report": state.get("news_report", ""),
            "fundamental_report": state.get("fundamental_report", ""),
            "technical_screening": state.get("technical_screening", []),
            "news_screening": state.get("news_screening", []),
            "fundamental_screening": state.get("fundamental_screening", []),
        },
        compliance_summary={
            "status": preview["ips_status"],
            "breaches": preview["ips_breaches"],
        },
    )
    return {
        "trade_preview": preview,
        "stored_decision": stored_decision,
    }


workflow = StateGraph(AgentState)

workflow.add_node("load_baseline_inputs", load_baseline_inputs_node)
workflow.add_node("technical_screen", technical_screen_node)
workflow.add_node("news_screen", news_screen_node)
workflow.add_node("fundamental_screen", fundamental_screen_node)
workflow.add_node("build_shared_deep_analysis_set", build_shared_deep_analysis_set_node)
workflow.add_node("technical_deep_analysis", technical_deep_analysis_node)
workflow.add_node("news_deep_analysis", news_deep_analysis_node)
workflow.add_node("fundamental_deep_analysis", fundamental_deep_analysis_node)
workflow.add_node("portfolio_manager", portfolio_manager_node)
workflow.add_node("build_trade_preview", build_trade_preview_node)

workflow.set_entry_point("load_baseline_inputs")
workflow.add_edge("load_baseline_inputs", "technical_screen")
workflow.add_edge("technical_screen", "news_screen")
workflow.add_edge("news_screen", "fundamental_screen")
workflow.add_edge("fundamental_screen", "build_shared_deep_analysis_set")
workflow.add_edge("build_shared_deep_analysis_set", "technical_deep_analysis")
workflow.add_edge("technical_deep_analysis", "news_deep_analysis")
workflow.add_edge("news_deep_analysis", "fundamental_deep_analysis")
workflow.add_edge("fundamental_deep_analysis", "portfolio_manager")
workflow.add_edge("portfolio_manager", "build_trade_preview")
workflow.add_edge("build_trade_preview", END)

app = workflow.compile()
