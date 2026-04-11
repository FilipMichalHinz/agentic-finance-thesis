"""Baseline Fundamental Analyst.

The baseline fundamental step reads prepared package data only. This keeps the
daily workflow reproducible and avoids live data calls during runtime.
"""

import json
from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage
from src.integrations.google_genai import build_default_agent_llm, response_content_to_text
from src.state import AgentState


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _screen_row(row: Dict[str, Any]) -> Dict[str, Any]:
    pe = _to_float(row.get("price_to_earnings"))
    price_to_sales = _to_float(row.get("price_to_sales"))
    price_move = abs(_to_float(row.get("chg_close_vs_prev_close_pct")))
    filing_flag = bool(row.get("filing_flag"))

    flagged = filing_flag or pe >= 30.0 or price_to_sales >= 5.0 or price_move >= 3.0
    trigger = []
    if filing_flag:
        trigger.append("fresh filing signal")
    if pe >= 30.0:
        trigger.append(f"high P/E {pe:.2f}")
    if price_to_sales >= 5.0:
        trigger.append(f"high P/S {price_to_sales:.2f}")
    if price_move >= 3.0:
        trigger.append(f"price move {price_move:.2f}%")

    return {
        "ticker": row["ticker"],
        "status": "flag_for_deep_analysis" if flagged else "no_issue",
        "trigger_reason": ", ".join(trigger) if trigger else "No major fundamental trigger",
        "rationale": (
            "Valuation or filing signals suggest the stock deserves closer review."
            if flagged
            else "The screening package does not show a strong new fundamental trigger."
        ),
    }


def fundamental_screen_node(state: AgentState):
    rows = state["daily_packages"]["fundamental"]["stocks"]
    screening = [_screen_row(row) for row in rows]
    return {"fundamental_screening": screening}


def fundamental_deep_analysis_node(state: AgentState):
    deep_set = set(state.get("shared_deep_analysis_set", []))
    rows = [
        row
        for row in state["daily_packages"]["fundamental"]["stocks"]
        if row["ticker"] in deep_set
    ]
    if not rows:
        return {"fundamental_report": "No stocks entered the fundamental deep-analysis set today."}

    llm = build_default_agent_llm(temperature=0)
    shared_context = state["daily_packages"]["fundamental"].get("shared_context")
    system_prompt = """You are the Fundamental Analyst in a simple baseline portfolio workflow.

Use only the prepared package rows and shared macro context.
For each ticker, write a short section with:
- recommendation: bullish, neutral, bearish, or inconclusive
- confidence: low, medium, or high
- rationale: 2-3 sentences tied directly to valuation, filing, and macro fields

Keep the explanation simple enough for business students reading a baseline system.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Package date: {state['package_date']}\n"
                f"Shared macro context:\n{json.dumps(shared_context, indent=2, default=str)}\n\n"
                f"Fundamental rows:\n{json.dumps(rows, indent=2, default=str)}"
            )
        ),
    ]
    response = llm.invoke(messages)
    return {"fundamental_report": response_content_to_text(response.content)}
