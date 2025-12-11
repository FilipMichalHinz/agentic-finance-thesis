import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState


def get_market_news(ticker: str):
    """
    Fetches the top 5 recent news headlines for the ticker.
    """
    stock = yf.Ticker(ticker)
    news = stock.news
    
    # Clean the data to save tokens
    headlines = []
    if news:
        for n in news[:5]: # limit to 5 articles
            headlines.append(f"- {n.get('title')} (Source: {n.get('publisher')})")
    
    return "\n".join(headlines)

def sentiment_analyst_node(state: AgentState):
    ticker = state["ticker"]
    
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

    # 1. Harvest Data
    try:
        raw_news = get_market_news(ticker)
    except Exception as e:
        raw_news = f"Error fetching news: {e}"
        
    if not raw_news:
        raw_news = "No recent news found."

    # 2. Analyze (The System Prompt)
    system_prompt = """You are a Sentiment Analyst for a Hedge Fund.
    Your job is to read news headlines and determine the 'Market Mood'.
    
    OUTPUT FORMAT:
    - Sentiment Score: (Float) -1.0 (Extreme Fear) to 1.0 (Extreme Greed).
    - Analysis: A one-sentence summary of the news drivers.
    """
    
    user_message = f"Analyze these headlines for {ticker}:\n{raw_news}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    response = llm.invoke(messages)
    
    # 3. Simple Parsing (We assume the model follows instructions)
    # In a real app, we would use regex or structured output to extract the float safely.
    content = response.content
    
    return {
        "sentiment_analysis": content,
        # We store the raw string for the CIO to read
    }