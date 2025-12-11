from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState  # Note: Absolute import assuming run from root

# Initialize the "Brain" (Gemini 3.0 Pro)
# We use a slightly higher temperature (0.4) to allow for creative strategy

def cio_agent_node(state: AgentState):
    """
    The CIO Agent synthesizes data and proposes a trade.
    It adapts if the Risk Manager rejected the previous attempt.
    """
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.4
)
    # 1. Unpack the State (Read the inputs)
    ticker = state["ticker"]
    sentiment = state.get("sentiment_analysis", "No Data")
    fundamentals = state.get("fundamental_analysis", "No Data")
    technicals = state.get("technical_analysis", "No Data")
    
    # 2. Check for Rejection History
    # If the Risk Manager said "NO", we need to know why.
    risk_feedback = state.get("risk_analysis", "None")
    revision_count = state.get("revision_count", 0)
    
    # 3. Define the Persona
    system_prompt = """You are the Chief Investment Officer (CIO) of a top-tier hedge fund.
    Your GOAL: Maximize Alpha (returns) while strictly adhering to risk feedback.
    
    INPUTS:
    - You have reports from Sentiment, Fundamental, and Technical analysts.
    - You may have REJECTION FEEDBACK from the Risk Manager.
    
    TASK:
    - Synthesize the signals into a coherent trade decision (Buy, Sell, or Hold).
    - If this is a RETRY (previous rejection), you MUST adjust your strategy to satisfy the Risk Manager.
    - Be decisive but professional.
    
    OUTPUT FORMAT:
    Provide a JSON-compatible response (do not wrap in ```json``` blocks if possible):
    {
      "allocation": "Buy 5% of Portfolio" or "Sell entire position",
      "reasoning": "Your concise logic here..."
    }
    """
    
    # 4. Construct the User Prompt
    if revision_count > 0:
        # This is a "Retry" scenario
        user_message = f"""
        WARNING: Your previous trade was REJECTED by Risk Management.
        Attempts made: {revision_count}
        
        RISK MANAGER FEEDBACK: "{risk_feedback}"
        
        You must propose a NEW strategy for {ticker} that addresses this feedback immediately.
        
        Current Market Data:
        - Sentiment: {sentiment}
        - Fundamentals: {fundamentals}
        - Technicals: {technicals}
        """
    else:
        # This is a fresh trade
        user_message = f"""
        Please generate a trade proposal for {ticker} based on the following analysis:
        
        - Sentiment Analyst: {sentiment}
        - Fundamental Analyst: {fundamentals}
        - Technical Analyst: {technicals}
        """

    # 5. Invoke the AI
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    response = llm.invoke(messages)
    
    # 6. Parse the Output (Simple Logic for now)
    # In a full build, we would use LangChain's JsonOutputParser
    content = response.content
    
    # Return the updates to the state
    return {
        "cio_portfolio_allocation": content, # Ideally parsed to just the action
        "cio_reasoning": content             # ideally parsed to just the logic
    }