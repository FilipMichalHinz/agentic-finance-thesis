"""Supabase persistence helpers for runtime portfolio records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.integrations.portfolio_logic import (
    PORTFOLIO_IPS,
    build_portfolio_snapshot,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_supabase_client():
    from src.integrations.supabase_client import get_supabase_client

    return get_supabase_client()


def _latest_row(table_name: str, run_id: str, order_field: str) -> Optional[Dict[str, Any]]:
    supabase = _get_supabase_client()
    response = (
        supabase.table(table_name)
        .select("*")
        .eq("run_id", run_id)
        .order(order_field, desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def _state_record(run_id: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "as_of_date": snapshot["as_of_date"],
        "cash": snapshot["cash"],
        "gross_market_value": snapshot["gross_market_value"],
        "total_value": snapshot["total_value"],
        "positions": snapshot["positions"],
        "recent_actions": snapshot["recent_actions"],
        "metrics": snapshot["metrics"],
        "updated_at": _utc_now_iso(),
    }


def _history_record(
    run_id: str,
    trade_date: str,
    snapshot: Dict[str, Any],
    as_of_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "trade_date": trade_date,
        "as_of_timestamp": as_of_timestamp,
        "cash": snapshot["cash"],
        "gross_market_value": snapshot["gross_market_value"],
        "total_value": snapshot["total_value"],
        "positions": snapshot["positions"],
        "recent_actions": snapshot["recent_actions"],
        "metrics": snapshot["metrics"],
    }


# Run configuration
def get_portfolio_run(run_id: str) -> Optional[Dict[str, Any]]:
    supabase = _get_supabase_client()
    response = (
        supabase.table("portfolio_runs")
        .select("*")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def ensure_portfolio_run(
    run_id: str,
    config_name: Optional[str] = None,
    initial_cash: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    existing = get_portfolio_run(run_id)

    record = {
        "run_id": run_id,
        "config_name": config_name or (existing or {}).get("config_name"),
        "universe_name": PORTFOLIO_IPS["universe_name"],
        "initial_cash": initial_cash if initial_cash is not None else (existing or {}).get("initial_cash"),
        "metadata": metadata or (existing or {}).get("metadata") or {},
        "updated_at": _utc_now_iso(),
    }
    if not existing:
        record["started_at"] = _utc_now_iso()

    supabase = _get_supabase_client()
    supabase.table("portfolio_runs").upsert(record, on_conflict="run_id").execute()
    return get_portfolio_run(run_id) or record


# Current and historical state
def upsert_portfolio_state(
    run_id: str,
    as_of_date: str,
    cash: Any,
    positions: Optional[Sequence[Dict[str, Any]]],
    recent_actions: Optional[Sequence[Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_portfolio_run(run_id)
    snapshot = build_portfolio_snapshot(
        as_of_date=as_of_date,
        cash=cash,
        positions=positions,
        recent_actions=recent_actions,
        metrics=metrics,
    )
    supabase = _get_supabase_client()
    supabase.table("portfolio_state").upsert(_state_record(run_id, snapshot), on_conflict="run_id").execute()
    snapshot["run_id"] = run_id
    return snapshot


def append_portfolio_history(
    run_id: str,
    trade_date: str,
    cash: Any,
    positions: Optional[Sequence[Dict[str, Any]]],
    recent_actions: Optional[Sequence[Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    as_of_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_portfolio_run(run_id)
    snapshot = build_portfolio_snapshot(
        as_of_date=trade_date,
        cash=cash,
        positions=positions,
        recent_actions=recent_actions,
        metrics=metrics,
    )
    supabase = _get_supabase_client()
    supabase.table("portfolio_history").upsert(
        _history_record(run_id, trade_date, snapshot, as_of_timestamp=as_of_timestamp),
        on_conflict="run_id,trade_date",
    ).execute()
    snapshot["run_id"] = run_id
    return snapshot


def get_current_portfolio_state(run_id: str) -> Optional[Dict[str, Any]]:
    supabase = _get_supabase_client()
    response = (
        supabase.table("portfolio_state")
        .select("*")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    row = rows[0] if rows else _latest_row("portfolio_history", run_id, "trade_date")
    if not row:
        return None

    snapshot = build_portfolio_snapshot(
        as_of_date=row.get("as_of_date") or row.get("trade_date"),
        cash=row.get("cash"),
        positions=row.get("positions"),
        recent_actions=row.get("recent_actions"),
        metrics=row.get("metrics"),
    )
    snapshot["run_id"] = run_id
    return snapshot


def load_portfolio_history_snapshots(
    run_id: str,
    lookback_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    supabase = _get_supabase_client()
    response = (
        supabase.table("portfolio_history")
        .select("*")
        .eq("run_id", run_id)
        .order("trade_date")
        .execute()
    )
    rows = response.data or []
    snapshots = [
        build_portfolio_snapshot(
            as_of_date=row["trade_date"],
            cash=row.get("cash"),
            positions=row.get("positions"),
            recent_actions=row.get("recent_actions"),
            metrics=row.get("metrics"),
        )
        for row in rows
    ]
    if lookback_days is not None and lookback_days > 0:
        snapshots = snapshots[-lookback_days:]

    return snapshots


# Decision log
def record_portfolio_decision(
    run_id: str,
    decision_date: str,
    execution_date: Optional[str],
    target_weights: Dict[str, Any],
    action_plan: Sequence[Dict[str, Any]],
    rationale: Optional[str] = None,
    analyst_inputs: Optional[Dict[str, Any]] = None,
    compliance_summary: Optional[Dict[str, Any]] = None,
    as_of_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_portfolio_run(run_id)
    record = {
        "run_id": run_id,
        "decision_date": decision_date,
        "execution_date": execution_date,
        "as_of_timestamp": as_of_timestamp,
        "target_weights": target_weights,
        "action_plan": list(action_plan),
        "rationale": rationale,
        "analyst_inputs": analyst_inputs or {},
        "compliance_summary": compliance_summary or {},
    }

    supabase = _get_supabase_client()
    supabase.table("portfolio_decisions").upsert(record, on_conflict="run_id,decision_date").execute()
    response = (
        supabase.table("portfolio_decisions")
        .select("*")
        .eq("run_id", run_id)
        .eq("decision_date", decision_date)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else record
