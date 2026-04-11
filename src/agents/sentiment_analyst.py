"""Baseline News Analyst.

The file keeps its historical filename for compatibility, but its role in the
baseline is the bounded News Analyst from the artifact spec.
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
    news_count = int(row.get("daily_news_count") or 0)
    price_move = abs(_to_float(row.get("chg_close_vs_prev_close_pct")))
    flagged = news_count > 0 or price_move >= 3.0
    trigger = []
    if news_count > 0:
        trigger.append(f"{news_count} stock-news item(s)")
    if price_move >= 3.0:
        trigger.append(f"price move {price_move:.2f}%")

    return {
        "ticker": row["ticker"],
        "status": "flag_for_deep_analysis" if flagged else "no_issue",
        "trigger_reason": ", ".join(trigger) if trigger else "Quiet news day",
        "rationale": (
            "The stock had fresh news or an unusually large move that merits a closer look."
            if flagged
            else "No stock-specific news signal stands out in the screening package."
        ),
    }


def news_screen_node(state: AgentState):
    rows = state["daily_packages"]["news"]["stocks"]
    screening = [_screen_row(row) for row in rows]
    return {"news_screening": screening}


def news_deep_analysis_node(state: AgentState):
    deep_set = set(state.get("shared_deep_analysis_set", []))
    rows = [
        row
        for row in state["daily_packages"]["news"]["stocks"]
        if row["ticker"] in deep_set
    ]
    if not rows:
        return {"news_report": "No stocks entered the news deep-analysis set today."}

    llm = build_default_agent_llm(temperature=0)
    shared_context = state["daily_packages"]["news"].get("shared_context")
    system_prompt = """You are the News Analyst in a simple baseline portfolio workflow.

Use only the provided package rows and shared market-news context.
For each ticker, write a short section with:
- recommendation: bullish, neutral, bearish, or inconclusive
- confidence: low, medium, or high
- rationale: 2-3 sentences tied directly to the news package fields

Treat general news as market context. Do not invent article details.
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Package date: {state['package_date']}\n"
                f"Shared market-news context:\n{json.dumps(shared_context, indent=2, default=str)}\n\n"
                f"Stock rows:\n{json.dumps(rows, indent=2, default=str)}"
            )
        ),
    ]
    response = llm.invoke(messages)
    return {"news_report": response_content_to_text(response.content)}
