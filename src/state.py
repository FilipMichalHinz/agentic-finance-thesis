#In LangGraph, the "State" is a Python class that holds the memory shared between all agents in the system. 
#Let's say if the Sentiment Analyst finds a bad news, it writes it here so the CIO can read it.

import operator
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict

class AgentState(TypedDict):
    """
    The shared memory of the system. 
    Now perfectly aligned with your Architecture Diagram.
    """
    
    # 1. The Input
    ticker: str
    
    # 2. Data Layer (The 3 Analysts)
    # Stream A: Sentiment (News)
    sentiment_score: Optional[float]     # -1.0 to +1.0
    sentiment_analysis: Optional[str]    # "Positive mentions of new CEO..."
    
    # Stream B: Fundamentals (Filings)
    fundamental_metrics: Optional[Dict]  # P/E, Revenue, Debt/Equity
    fundamental_analysis: Optional[str]  # "Strong balance sheet but slowing growth..."
    
    # Stream C: Technicals (Price Action) -- NEW!
    technical_signals: Optional[Dict]    # RSI, MACD, Bollinger Bands
    technical_analysis: Optional[str]    # "Stock is oversold, potential bounce..."
    
    # 3. Strategic Layer (CIO)
    cio_portfolio_allocation: Optional[str] 
    cio_reasoning: Optional[str]
    
    # 4. Oversight Layer (Risk Manager)
    risk_score: Optional[int]            # 0-10
    risk_analysis: Optional[str]
    risk_approved: bool                  # The Traffic Light
    
    # 5. System State
    revision_count: Annotated[int, operator.add] 
    messages: List[str]