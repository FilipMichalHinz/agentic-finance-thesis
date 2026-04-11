"""Small helpers for the baseline daily portfolio-management workflow.

This module intentionally keeps the baseline logic explicit and easy to inspect.
The helpers here support three jobs:
1. choose a valid prepared package date
2. keep the shared deep-analysis set deterministic
3. make the portfolio manager output safe enough for the deterministic preview step
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence

from src.integrations.daily_info_packages import get_latest_available_package_date
from src.integrations.portfolio_logic import PORTFOLIO_IPS
from src.integrations.portfolio_store import (
    ensure_portfolio_run,
    get_current_portfolio_state,
    upsert_portfolio_state,
)
from src.ticker_universes import DOW_30_TICKERS


UNIVERSE_TICKERS = set(DOW_30_TICKERS)


def resolve_package_date(requested_date: Optional[str] = None) -> str:
    text = (requested_date or "").strip()
    if text:
        return text[:10]
    latest = get_latest_available_package_date()
    if latest is None:
        raise RuntimeError(
            "No prepared daily screening packages were found in Supabase. "
            "Build the package tables before running the baseline workflow."
        )
    return latest


def extract_current_holdings(current_portfolio: Optional[Dict[str, Any]]) -> List[str]:
    if not current_portfolio:
        return []
    tickers = []
    for position in current_portfolio.get("positions", []):
        ticker = str(position.get("ticker", "")).strip().upper()
        if ticker:
            tickers.append(ticker)
    return sorted(set(tickers))


def build_shared_deep_analysis_set(
    holdings: Sequence[str],
    screening_outputs: Iterable[Sequence[Dict[str, Any]]],
) -> List[str]:
    tickers = {str(ticker).strip().upper() for ticker in holdings if str(ticker).strip()}
    for analyst_rows in screening_outputs:
        for row in analyst_rows:
            if row.get("status") != "flag_for_deep_analysis":
                continue
            ticker = str(row.get("ticker", "")).strip().upper()
            if ticker:
                tickers.add(ticker)
    return sorted(tickers)


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = (text or "").strip()
    if not cleaned:
        return None

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    snippet = cleaned[start : end + 1]
    try:
        parsed = json.loads(snippet)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def fallback_target_weights(candidate_tickers: Sequence[str]) -> Dict[str, float]:
    tickers = [ticker for ticker in candidate_tickers if ticker in UNIVERSE_TICKERS]
    if not tickers:
        return {"CASH": 1.0}

    count = min(5, len(tickers))
    stock_weight = min(PORTFOLIO_IPS["max_position_weight"], 0.60 / count)
    weights = {ticker: stock_weight for ticker in tickers[:count]}
    weights["CASH"] = round(1.0 - sum(weights.values()), 4)
    return normalize_weights(weights)


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    positive = {ticker: float(weight) for ticker, weight in weights.items() if float(weight) > 0}
    total = sum(positive.values())
    if total <= 0:
        return {"CASH": 1.0}
    normalized = {ticker: round(weight / total, 4) for ticker, weight in positive.items()}

    # Adjust the final cash value so the printed weights sum to exactly 1.0.
    if "CASH" in normalized:
        remainder = 1.0 - sum(weight for ticker, weight in normalized.items() if ticker != "CASH")
        normalized["CASH"] = round(max(remainder, 0.0), 4)
    else:
        remainder = round(1.0 - sum(normalized.values()), 4)
        if remainder > 0:
            normalized["CASH"] = remainder
    return normalized


def sanitize_target_weights(
    raw_target_weights: Optional[Dict[str, Any]],
    allowed_tickers: Sequence[str],
) -> Dict[str, float]:
    if not raw_target_weights:
        return fallback_target_weights(allowed_tickers)

    allowed_set = {ticker for ticker in allowed_tickers if ticker in UNIVERSE_TICKERS}
    stock_items: List[tuple[str, float]] = []
    cash_weight = 0.0

    for raw_ticker, raw_weight in raw_target_weights.items():
        ticker = str(raw_ticker).strip().upper()
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        if ticker == "CASH":
            cash_weight = weight
            continue
        if ticker not in allowed_set:
            continue
        stock_items.append((ticker, min(weight, PORTFOLIO_IPS["max_position_weight"])))

    # Keep the PM output easy to understand by capping the active names.
    deduped: Dict[str, float] = {}
    for ticker, weight in stock_items:
        deduped[ticker] = max(deduped.get(ticker, 0.0), weight)

    trimmed = sorted(deduped.items(), key=lambda item: item[1], reverse=True)[:5]
    if not trimmed:
        return fallback_target_weights(allowed_tickers)

    stock_sum = sum(weight for _, weight in trimmed)
    target_weights = {ticker: weight for ticker, weight in trimmed}
    target_weights["CASH"] = max(cash_weight, 1.0 - stock_sum)
    return normalize_weights(target_weights)


def load_or_initialize_portfolio_state(
    run_id: str,
    package_date: str,
    initial_cash: float,
) -> Dict[str, Any]:
    ensure_portfolio_run(
        run_id=run_id,
        config_name="baseline",
        initial_cash=initial_cash,
        metadata={"workflow": "simple_baseline"},
    )
    current_state = get_current_portfolio_state(run_id)
    if current_state is not None:
        return current_state

    # The baseline starts from cash if no prior simulated portfolio exists.
    return upsert_portfolio_state(
        run_id=run_id,
        as_of_date=package_date,
        cash=initial_cash,
        positions=[],
        recent_actions=[],
        metrics={"source": "baseline_initialization"},
    )
