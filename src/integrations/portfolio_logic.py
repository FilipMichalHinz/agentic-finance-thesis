"""Deterministic portfolio math, fixed IPS checks, and rebalance preview helpers."""

from __future__ import annotations

import math
from datetime import date, datetime
from statistics import stdev
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.ticker_universes import DOW_30_TICKERS

EPSILON = 1e-9

# The thesis uses one fixed policy, so runtime logic reads this constant directly.
PORTFOLIO_IPS: Dict[str, Any] = {
    "long_only": True,
    "allow_leverage": False,
    "universe_name": "DJIA30",
    "max_position_weight": 0.15,
    "cash_min_weight": 0.0,
    "cash_max_weight": 0.30,
    "min_holdings": 5,
    "max_holdings": 10,
    "min_rebalance_weight_change": 0.005,
}

UNIVERSE_MEMBERS = {
    "DJIA30": set(DOW_30_TICKERS),
    "DOW_30": set(DOW_30_TICKERS),
}


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_iso_date(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("Expected a non-empty ISO date or timestamp")
    if "T" not in text:
        return date.fromisoformat(text).isoformat()
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()


# Snapshot helpers
def _normalize_positions(raw_positions: Optional[Sequence[Dict[str, Any]]], cash: float) -> Dict[str, Any]:
    positions: List[Dict[str, Any]] = []

    for raw_position in raw_positions or []:
        ticker = str(raw_position.get("ticker", "")).strip().upper()
        if not ticker:
            continue

        qty = to_float(raw_position.get("qty"))
        close_price = raw_position.get("close_price")
        if close_price is None:
            close_price = raw_position.get("price")
        if close_price is None:
            close_price = raw_position.get("reference_price")
        close_price_float = None if close_price is None else to_float(close_price)

        market_value = raw_position.get("market_value")
        if market_value is None and close_price_float is not None:
            market_value = qty * close_price_float
        market_value_float = to_float(market_value)

        if abs(qty) <= EPSILON and abs(market_value_float) <= EPSILON:
            continue

        positions.append(
            {
                "ticker": ticker,
                "qty": qty,
                "close_price": close_price_float,
                "market_value": market_value_float,
            }
        )

    gross_market_value = sum(position["market_value"] for position in positions)
    total_value = cash + gross_market_value
    cash_weight = 0.0 if total_value <= EPSILON else cash / total_value

    for position in positions:
        position["weight"] = 0.0 if total_value <= EPSILON else position["market_value"] / total_value

    positions.sort(key=lambda position: (-position["weight"], position["ticker"]))

    return {
        "cash_weight": cash_weight,
        "gross_market_value": gross_market_value,
        "holdings_count": len(positions),
        "positions": positions,
        "total_value": total_value,
    }


def build_portfolio_snapshot(
    as_of_date: str,
    cash: Any,
    positions: Optional[Sequence[Dict[str, Any]]],
    recent_actions: Optional[Sequence[Any]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cash_float = to_float(cash)
    normalized = _normalize_positions(raw_positions=positions, cash=cash_float)
    return {
        "as_of_date": as_of_date,
        "cash": cash_float,
        "cash_weight": normalized["cash_weight"],
        "gross_market_value": normalized["gross_market_value"],
        "holdings_count": normalized["holdings_count"],
        "metrics": metrics or {},
        "positions": normalized["positions"],
        "recent_actions": list(recent_actions or []),
        "total_value": normalized["total_value"],
    }


# Risk and IPS helpers
def _extract_returns(history_snapshots: Sequence[Dict[str, Any]]) -> List[float]:
    returns: List[float] = []
    previous_total_value = None

    for snapshot in history_snapshots:
        total_value = to_float(snapshot.get("total_value"))
        if previous_total_value is not None and previous_total_value > EPSILON and total_value > EPSILON:
            returns.append(total_value / previous_total_value - 1.0)
        previous_total_value = total_value

    return returns


def _annualized_volatility(returns: Sequence[float], min_points: int) -> Optional[float]:
    if len(returns) < min_points:
        return None
    if len(returns) < 2:
        return 0.0
    return stdev(returns) * math.sqrt(252)


def _current_drawdown(history_snapshots: Sequence[Dict[str, Any]]) -> Optional[float]:
    peak = None
    current_drawdown = None

    for snapshot in history_snapshots:
        total_value = to_float(snapshot.get("total_value"))
        if total_value <= EPSILON:
            continue
        peak = total_value if peak is None else max(peak, total_value)
        current_drawdown = total_value / peak - 1.0

    return current_drawdown


def summarize_portfolio_risk(
    current_state: Dict[str, Any],
    history_snapshots: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    weights = [max(to_float(position.get("weight")), 0.0) for position in current_state.get("positions", [])]
    weights.sort(reverse=True)
    returns = _extract_returns(history_snapshots)

    return {
        "as_of_date": current_state["as_of_date"],
        "portfolio_value": current_state["total_value"],
        "cash_weight": current_state["cash_weight"],
        "holdings_count": current_state["holdings_count"],
        "max_position_weight": weights[0] if weights else 0.0,
        "top_3_weight": sum(weights[:3]),
        "hhi": sum(weight * weight for weight in weights),
        "rolling_20d_vol": _annualized_volatility(returns[-20:], min_points=20),
        "rolling_60d_vol": _annualized_volatility(returns[-60:], min_points=60),
        "current_drawdown": _current_drawdown(history_snapshots),
        "history_points": len(history_snapshots),
    }


def summarize_portfolio_compliance(
    current_state: Dict[str, Any],
) -> Dict[str, Any]:
    positions = current_state.get("positions", [])
    universe_members = UNIVERSE_MEMBERS.get(PORTFOLIO_IPS["universe_name"], set())

    overweight_tickers = [
        {"ticker": position["ticker"], "weight": position["weight"]}
        for position in positions
        if position["weight"] > PORTFOLIO_IPS["max_position_weight"] + EPSILON
    ]
    out_of_universe = [
        position["ticker"]
        for position in positions
        if universe_members and position["ticker"] not in universe_members
    ]

    breaches: List[Dict[str, Any]] = []
    holdings_count = current_state["holdings_count"]
    cash_weight = current_state["cash_weight"]

    if holdings_count < PORTFOLIO_IPS["min_holdings"] or holdings_count > PORTFOLIO_IPS["max_holdings"]:
        breaches.append(
            {
                "rule": "holdings_count",
                "actual": holdings_count,
                "min": PORTFOLIO_IPS["min_holdings"],
                "max": PORTFOLIO_IPS["max_holdings"],
            }
        )

    if cash_weight < PORTFOLIO_IPS["cash_min_weight"] - EPSILON or cash_weight > PORTFOLIO_IPS["cash_max_weight"] + EPSILON:
        breaches.append(
            {
                "rule": "cash_weight",
                "actual": cash_weight,
                "min": PORTFOLIO_IPS["cash_min_weight"],
                "max": PORTFOLIO_IPS["cash_max_weight"],
            }
        )

    if overweight_tickers:
        breaches.append(
            {
                "rule": "max_position_weight",
                "limit": PORTFOLIO_IPS["max_position_weight"],
                "positions": overweight_tickers,
            }
        )

    if out_of_universe:
        breaches.append(
            {
                "rule": "universe_membership",
                "universe_name": PORTFOLIO_IPS["universe_name"],
                "tickers": out_of_universe,
            }
        )

    return {
        "as_of_date": current_state["as_of_date"],
        "cash_weight": cash_weight,
        "holdings_count": holdings_count,
        "ips": PORTFOLIO_IPS,
        "max_position_weight": max((position["weight"] for position in positions), default=0.0),
        "overweight_tickers": overweight_tickers,
        "out_of_universe_tickers": out_of_universe,
        "status": "pass" if not breaches else "fail",
        "breaches": breaches,
    }


# Rebalance preview helpers
def _normalize_target_weights(target_weights: Dict[str, Any]) -> Tuple[Dict[str, float], Optional[float], float]:
    stock_weights: Dict[str, float] = {}
    explicit_cash_weight = None

    for raw_ticker, raw_weight in target_weights.items():
        ticker = str(raw_ticker).strip().upper()
        if not ticker:
            continue

        weight = to_float(raw_weight)
        if ticker == "CASH":
            explicit_cash_weight = weight
            continue

        if abs(weight) <= EPSILON:
            continue

        stock_weights[ticker] = weight

    return stock_weights, explicit_cash_weight, sum(stock_weights.values())


def resolve_reference_prices(
    current_state: Dict[str, Any],
    tickers: Iterable[str],
    as_of: str,
) -> Dict[str, Optional[float]]:
    from src.integrations.market_prices import get_latest_price_before

    existing_positions = {
        position["ticker"]: position
        for position in current_state.get("positions", [])
    }
    prices: Dict[str, Optional[float]] = {}

    for ticker in tickers:
        position = existing_positions.get(ticker)
        if position and position.get("close_price") is not None:
            prices[ticker] = to_float(position["close_price"])
            continue

        market_price = get_latest_price_before(ticker=ticker, as_of=as_of)
        if not market_price or market_price.get("price_close") is None:
            prices[ticker] = None
            continue

        prices[ticker] = to_float(market_price["price_close"])

    return prices


def build_rebalance_preview(
    current_state: Dict[str, Any],
    target_weights: Dict[str, Any],
    reference_prices: Dict[str, Optional[float]],
    rationale: Optional[str] = None,
) -> Dict[str, Any]:
    stock_weights, explicit_cash_weight, stock_weight_sum = _normalize_target_weights(target_weights)
    target_cash_weight = 1.0 - stock_weight_sum if explicit_cash_weight is None else explicit_cash_weight

    current_positions = {
        position["ticker"]: position
        for position in current_state.get("positions", [])
    }
    portfolio_value = to_float(current_state.get("total_value"))
    if portfolio_value <= EPSILON:
        raise ValueError("Current portfolio total_value must be positive to preview a rebalance")

    actions: List[Dict[str, Any]] = []
    turnover_value = 0.0
    min_trade_weight = PORTFOLIO_IPS["min_rebalance_weight_change"]

    for ticker in sorted(set(current_positions) | set(stock_weights)):
        current_position = current_positions.get(ticker, {})
        current_weight = to_float(current_position.get("weight"))
        current_value = to_float(current_position.get("market_value"))
        target_weight = stock_weights.get(ticker, 0.0)
        target_value = target_weight * portfolio_value
        delta_weight = target_weight - current_weight
        delta_value = target_value - current_value
        reference_price = reference_prices.get(ticker)

        if abs(delta_weight) < min_trade_weight:
            action_type = "hold"
            side = "hold"
            trade_value = 0.0
        elif current_value <= EPSILON and target_value > EPSILON:
            action_type = "buy"
            side = "buy"
            trade_value = delta_value
        elif target_value <= EPSILON and current_value > EPSILON:
            action_type = "sell"
            side = "sell"
            trade_value = abs(delta_value)
        elif delta_value > 0:
            action_type = "increase"
            side = "buy"
            trade_value = delta_value
        else:
            action_type = "reduce"
            side = "sell"
            trade_value = abs(delta_value)

        turnover_value += trade_value
        estimated_qty = 0.0 if reference_price in (None, 0.0) else abs(delta_value) / reference_price

        actions.append(
            {
                "ticker": ticker,
                "action_type": action_type,
                "side": side,
                "current_weight": current_weight,
                "target_weight": target_weight,
                "current_value": current_value,
                "target_value": target_value,
                "delta_weight": delta_weight,
                "delta_value": delta_value,
                "reference_price": reference_price,
                "estimated_qty": 0.0 if action_type == "hold" else estimated_qty,
                "rationale": rationale,
            }
        )

    target_snapshot = build_portfolio_snapshot(
        as_of_date=current_state["as_of_date"],
        cash=target_cash_weight * portfolio_value,
        positions=[
            {
                "ticker": ticker,
                "qty": 0.0,
                "close_price": reference_prices.get(ticker),
                "market_value": weight * portfolio_value,
            }
            for ticker, weight in sorted(stock_weights.items())
        ],
    )
    compliance = summarize_portfolio_compliance(current_state=target_snapshot)

    negative_weights = [
        {"ticker": ticker, "weight": weight}
        for ticker, weight in stock_weights.items()
        if weight < -EPSILON
    ]
    if PORTFOLIO_IPS["long_only"] and negative_weights:
        compliance["breaches"].append({"rule": "long_only", "positions": negative_weights})
        compliance["status"] = "fail"

    if not PORTFOLIO_IPS["allow_leverage"] and (stock_weight_sum > 1.0 + EPSILON or target_cash_weight < -EPSILON):
        compliance["breaches"].append(
            {
                "rule": "no_leverage",
                "stock_weight_sum": stock_weight_sum,
                "target_cash_weight": target_cash_weight,
            }
        )
        compliance["status"] = "fail"

    missing_prices = [
        ticker
        for ticker, price in reference_prices.items()
        if price is None and (ticker in stock_weights or ticker in current_positions)
    ]

    return {
        "as_of_date": current_state["as_of_date"],
        "portfolio_value": portfolio_value,
        "current_cash_weight": current_state["cash_weight"],
        "target_cash_weight": target_cash_weight,
        "requested_stock_weight_sum": stock_weight_sum,
        "estimated_turnover": 0.0 if portfolio_value <= EPSILON else turnover_value / portfolio_value,
        "missing_prices": sorted(missing_prices),
        "ips_breaches": compliance["breaches"],
        "ips_status": compliance["status"],
        "actions": sorted(actions, key=lambda action: (-abs(action["delta_value"]), action["ticker"])),
    }
