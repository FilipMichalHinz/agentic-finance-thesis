"""Baseline Technical Analyst.

The baseline uses prepared daily package rows instead of live API calls. This
keeps the runtime point-in-time safe and easier to explain.
"""

import json
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
from src.integrations.google_genai import build_default_agent_llm, response_content_to_text
from src.state import AgentState

def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _screen_row(row: Dict[str, Any]) -> Dict[str, Any]:
    price_move = abs(_to_float(row.get("chg_close_vs_prev_close_pct")))
    rsi_change = abs(_to_float(row.get("chg_rsi")))
    adx_change = abs(_to_float(row.get("chg_adx")))
    volatility_change = abs(_to_float(row.get("chg_standarddeviation")))

    flagged = (
        price_move >= 2.0
        or rsi_change >= 4.0
        or adx_change >= 2.0
        or volatility_change >= 2.0
    )
    trigger_bits = []
    if price_move >= 2.0:
        trigger_bits.append(f"price move {price_move:.2f}%")
    if rsi_change >= 4.0:
        trigger_bits.append(f"RSI change {rsi_change:.2f}")
    if adx_change >= 2.0:
        trigger_bits.append(f"ADX change {adx_change:.2f}")
    if volatility_change >= 2.0:
        trigger_bits.append(f"volatility change {volatility_change:.2f}")

    return {
        "ticker": row["ticker"],
        "status": "flag_for_deep_analysis" if flagged else "no_issue",
        "trigger_reason": ", ".join(trigger_bits) if trigger_bits else "No unusual technical move",
        "rationale": (
            "Technical package shows an unusually large move or indicator shift."
            if flagged
            else "Technical package looks routine for the day."
        ),
    }


def technical_screen_node(state: AgentState):
    rows = state["daily_packages"]["technical"]["stocks"]
    screening = [_screen_row(row) for row in rows]
    return {"technical_screening": screening}


def technical_deep_analysis_node(state: AgentState):
    deep_set = set(state.get("shared_deep_analysis_set", []))
    rows = [
        row
        for row in state["daily_packages"]["technical"]["stocks"]
        if row["ticker"] in deep_set
    ]
    if not rows:
        return {"technical_report": "No stocks entered the technical deep-analysis set today."}

    llm = build_default_agent_llm(temperature=0)
    system_prompt = """You are the Technical Analyst in a simple baseline portfolio workflow.

Use only the provided prepared package rows.
For each ticker, write a short section with:
- recommendation: bullish, neutral, bearish, or inconclusive
- confidence: low, medium, or high
- rationale: 2-3 sentences tied directly to the technical fields

Be concrete and simple. Do not discuss any data that is not present in the package.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Package date: {state['package_date']}\n"
                f"Technical rows:\n{json.dumps(rows, indent=2, default=str)}"
            )
        ),
    ]
    response = llm.invoke(messages)
    return {"technical_report": response_content_to_text(response.content)}
