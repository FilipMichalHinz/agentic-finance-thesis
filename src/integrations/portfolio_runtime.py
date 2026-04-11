"""Public portfolio runtime API.

Storage lives in `portfolio_store.py`.
Deterministic math and IPS checks live in `portfolio_logic.py`.
This file keeps a small import surface for the rest of the app.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.integrations.portfolio_logic import (
    PORTFOLIO_IPS,
    build_portfolio_snapshot,
    build_rebalance_preview,
    resolve_reference_prices,
    summarize_portfolio_compliance,
    summarize_portfolio_risk,
    to_iso_date,
)
from src.integrations.portfolio_store import (
    append_portfolio_history,
    ensure_portfolio_run,
    get_current_portfolio_state,
    load_portfolio_history_snapshots,
    record_portfolio_decision,
    upsert_portfolio_state,
)


def get_portfolio_compliance_summary(
    run_id: str,
    target_weights: Optional[Dict[str, Any]] = None,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    current_state = get_current_portfolio_state(run_id)
    if current_state is None:
        raise ValueError(f"No portfolio state found for run_id={run_id}")

    # The PM can either inspect the current portfolio or check a proposed target
    # allocation against the IPS before finalizing a decision.
    if target_weights is not None:
        preview = preview_rebalance(
            run_id=run_id,
            as_of=as_of or current_state["as_of_date"],
            target_weights=target_weights,
        )
        return {
            "run_id": run_id,
            "scope": "target",
            "as_of": preview["as_of"],
            "status": preview["ips_status"],
            "breaches": preview["ips_breaches"],
            "missing_prices": preview["missing_prices"],
            "target_cash_weight": preview["target_cash_weight"],
            "requested_stock_weight_sum": preview["requested_stock_weight_sum"],
        }

    summary = summarize_portfolio_compliance(current_state=current_state)
    summary["run_id"] = run_id
    summary["scope"] = "current"
    return summary


def get_portfolio_risk_summary(run_id: str, lookback_days: int = 60) -> Dict[str, Any]:
    current_state = get_current_portfolio_state(run_id)
    if current_state is None:
        raise ValueError(f"No portfolio state found for run_id={run_id}")

    history_snapshots = load_portfolio_history_snapshots(run_id, lookback_days=lookback_days)
    if not history_snapshots or history_snapshots[-1]["as_of_date"] != current_state["as_of_date"]:
        history_snapshots = [*history_snapshots, current_state]

    summary = summarize_portfolio_risk(
        current_state=current_state,
        history_snapshots=history_snapshots,
    )
    summary["run_id"] = run_id
    summary["lookback_days"] = lookback_days
    return summary


def preview_rebalance(
    run_id: str,
    as_of: str,
    target_weights: Dict[str, Any],
    rationale: Optional[str] = None,
) -> Dict[str, Any]:
    current_state = get_current_portfolio_state(run_id)
    if current_state is None:
        raise ValueError(f"No portfolio state found for run_id={run_id}")

    # Reuse stored close prices where possible and only fetch missing names.
    tickers = sorted(
        {
            position["ticker"]
            for position in current_state.get("positions", [])
        }
        | {
            str(ticker).strip().upper()
            for ticker in target_weights
            if str(ticker).strip().upper() != "CASH"
        }
    )
    reference_prices = resolve_reference_prices(current_state=current_state, tickers=tickers, as_of=as_of)

    preview = build_rebalance_preview(
        current_state=current_state,
        target_weights=target_weights,
        reference_prices=reference_prices,
        rationale=rationale,
    )
    preview["run_id"] = run_id
    preview["as_of"] = to_iso_date(as_of)
    return preview


__all__ = [
    "PORTFOLIO_IPS",
    "append_portfolio_history",
    "build_portfolio_snapshot",
    "build_rebalance_preview",
    "ensure_portfolio_run",
    "get_current_portfolio_state",
    "get_portfolio_compliance_summary",
    "get_portfolio_risk_summary",
    "preview_rebalance",
    "record_portfolio_decision",
    "summarize_portfolio_compliance",
    "summarize_portfolio_risk",
    "upsert_portfolio_state",
]
