import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.baseline_workflow import fallback_target_weights, parse_json_object, sanitize_target_weights
from src.integrations.google_genai import build_default_agent_llm, response_content_to_text
from src.integrations.portfolio_logic import PORTFOLIO_IPS
from src.state import AgentState


def portfolio_manager_node(state: AgentState):
    """
    The baseline Portfolio Manager is the single final decision-maker.

    It reads the three analyst reports and proposes target weights that the
    deterministic preview step can translate into action-ready trades.
    """

    deep_set = state.get("shared_deep_analysis_set", [])
    if not deep_set:
        return {
            "portfolio_decision": {
                "summary": "No stocks were flagged for deeper analysis, so the baseline stays in cash.",
                "target_weights": {"CASH": 1.0},
                "focus_tickers": [],
                "raw_response": "",
            }
        }

    llm = build_default_agent_llm(temperature=0)
    system_prompt = """You are the Portfolio Manager in a simple baseline workflow.

Your job is to turn three analyst reports into one target portfolio.
Keep the portfolio easy to understand:
- long only
- use only the tickers from the shared deep-analysis set
- each stock weight must be <= 0.15
- include CASH
- prefer 3 to 5 active stock positions when the evidence supports it

Return strict JSON with this shape:
{
  "summary": "short explanation",
  "focus_tickers": ["TICKER1", "TICKER2"],
  "target_weights": {
    "TICKER1": 0.15,
    "TICKER2": 0.15,
    "CASH": 0.70
  }
}
"""
    user_message = {
        "package_date": state["package_date"],
        "ips": PORTFOLIO_IPS,
        "current_portfolio": state["current_portfolio"],
        "shared_deep_analysis_set": deep_set,
        "technical_report": state.get("technical_report", ""),
        "news_report": state.get("news_report", ""),
        "fundamental_report": state.get("fundamental_report", ""),
    }
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(user_message, indent=2, default=str)),
    ]
    response = llm.invoke(messages)
    content = response_content_to_text(response.content)
    parsed = parse_json_object(content) or {}
    target_weights = sanitize_target_weights(parsed.get("target_weights"), deep_set)
    if target_weights == {"CASH": 1.0} and deep_set:
        target_weights = fallback_target_weights(deep_set)

    return {
        "portfolio_decision": {
            "summary": parsed.get("summary") or content,
            "focus_tickers": parsed.get("focus_tickers") or deep_set[:5],
            "target_weights": target_weights,
            "raw_response": content,
        }
    }
