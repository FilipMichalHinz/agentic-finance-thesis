import pandas as pd
import numpy as np
import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage
from src.integrations.google_genai import build_default_agent_llm, response_content_to_text
from src.state import AgentState


def fetch_price_data(ticker: str) -> pd.DataFrame:
    # We need a bit more history to find the major swing high/low for Fibs
    stock = yf.Ticker(ticker)
    df = stock.history(period="1y") 
    return df

def calculate_fibonacci_levels(df: pd.DataFrame) -> dict:
    """
    Finds the major Swing High and Swing Low over the last year 
    and calculates the key retracement levels.
    """
    max_price = df['High'].max()
    min_price = df['Low'].min()
    current_price = df['Close'].iloc[-1]
    
    diff = max_price - min_price
    
    # Standard Fibonacci Levels
    level_0 = max_price
    level_236 = max_price - (0.236 * diff)
    level_382 = max_price - (0.382 * diff)
    level_500 = max_price - (0.5 * diff)
    level_618 = max_price - (0.618 * diff) # The "Golden Pocket"
    level_100 = min_price

    # Determine where we are relative to the levels
    status = "In No Man's Land"
    dist_to_618 = abs(current_price - level_618) / current_price
    
    if dist_to_618 < 0.02: # Within 2% of the Golden Pocket
        status = "TESTING GOLDEN POCKET (0.618)"
    elif current_price > level_236:
        status = "Near Highs"
    elif current_price < level_618:
        status = "Deep Retracement (Bearish Territory)"

    return {
        "current_price": round(current_price, 2),
        "swing_high": round(max_price, 2),
        "swing_low": round(min_price, 2),
        "fib_level_0.618": round(level_618, 2),
        "fib_level_0.5": round(level_500, 2),
        "fib_status": status
    }

def calculate_indicators(df: pd.DataFrame) -> dict:
    if df.empty: return {}

    # 1. Get Fibonacci (The Priority)
    fib_data = calculate_fibonacci_levels(df)

    # 2. RSI (The Secondary Confirmation)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # 3. MACD (Trend Confirmation)
    short_ema = df['Close'].ewm(span=12, adjust=False).mean()
    long_ema = df['Close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()

    # Combine data
    return {
        **fib_data, # Unpack Fib data at the top level
        "rsi_14": round(rsi.iloc[-1], 2),
        "macd_signal": "Bullish" if macd.iloc[-1] > signal.iloc[-1] else "Bearish"
    }

def technical_analyst_node(state: AgentState):
    ticker = state["ticker"]
    
    llm = build_default_agent_llm(temperature=0)

    try:
        df = fetch_price_data(ticker)
        data = calculate_indicators(df)
        data_str = str(data)
    except Exception as e:
        data = {}
        data_str = f"Error: {e}"

    # --- THE UPDATED PROMPT ---
    system_prompt = """You are a Fibonacci-Focused Technical Analyst.
    
    YOUR STRATEGY:
    You rely mostly on Fibonacci Retracement levels. 
    - The 0.618 level ('Golden Pocket') is the most critical support zone.
    - If price is bouncing off 0.618, it is a HIGH CONVICTION BUY signal.
    - Use RSI and MACD only to confirm the Fib signal.
    
    INPUT DATA:
    - Fib Status: Tells you if we are near a key level.
    - RSI/MACD: Secondary indicators.
    
    OUTPUT:
    Provide a signal based primarily on where the price is relative to the Fibonacci levels.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyze {ticker}: {data_str}")
    ]
    
    response = llm.invoke(messages)
    response_text = response_content_to_text(response.content)
    
    return {
        "technical_signals": data,
        "technical_analysis": response_text
    }
