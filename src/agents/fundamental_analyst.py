import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage
from src.integrations.google_genai import build_default_agent_llm
from src.state import AgentState
from src.tools.sec_rag_tool import search_filings
from src.integrations.tool_runner import run_with_tools


def _response_to_text(content) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join([p for p in parts if p]).strip()
    if content is None:
        return ""
    return str(content)


def get_fundamentals(ticker: str):
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # We select only the key metrics to avoid confusing the AI
    return {
        "P/E Ratio": info.get("trailingPE"),
        "Forward P/E": info.get("forwardPE"),
        "DebtToEquity": info.get("debtToEquity"),
        "ProfitMargins": info.get("profitMargins"),
        "RevenueGrowth": info.get("revenueGrowth"),
        "FreeCashFlow": info.get("freeCashflow")
    }

def fundamental_analyst_node(state: AgentState):
    ticker = state["ticker"]
    as_of = state.get("as_of") or "2024-08-01T00:00:00Z"
    
    llm = build_default_agent_llm(temperature=0)
    try:
        metrics = get_fundamentals(ticker)
        metrics_str = str(metrics)
    except Exception as e:
        metrics_str = f"Error fetching fundamentals: {e}"

    system_prompt = """You are a Fundamental Analyst (Warren Buffett style).
    Evaluate the financial health of this company.
    
    Focus on:
    1. Valuation (Is it cheap?)
    2. Profitability (Are they making money?)
    3. Debt (Are they safe?)

    You should reference specific SEC filings to support your analysis when helpful.
    Use the search_filings tool to find relevant excerpts for the ticker and as_of time.
    Formulate your own query based on what you need (e.g., revenue, margins, cash flow, debt).
    If you use filings, cite them with form and timestamp.
    Always provide a final analysis, even if you do not use filings.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Analyze {ticker} financials (as_of={as_of}). "
                f"Basic metrics (secondary): {metrics_str}"
            )
        ),
    ]
    response = run_with_tools(llm, messages, tools=[search_filings], max_iterations=5)
    response_text = _response_to_text(response.content)
    
    return {
        "fundamental_analysis": response_text,
        "fundamental_metrics": metrics
    }
