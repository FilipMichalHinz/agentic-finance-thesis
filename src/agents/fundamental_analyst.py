import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState


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
    
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0
)
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
    """
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze {ticker} financials: {metrics_str}")
    ])
    
    return {
        "fundamental_analysis": response.content,
        "fundamental_metrics": metrics
    }