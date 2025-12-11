from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState

# Initialize the "Reasoning Model" (Gemini 3.0 Pro)
# We use a lower temperature (0.1) because Risk should be cold and logical.

def risk_manager_node(state: AgentState):
    """
    The Risk Manager evaluates the CIO's trade proposal.
    It acts as a 'Compliance Firewall'.
    """
    
    llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.1
)

    # 1. Gather the Evidence
    ticker = state["ticker"]
    cio_proposal = state.get("cio_portfolio_allocation", "No Action")
    cio_logic = state.get("cio_reasoning", "No Reasoning provided")
    
    # 2. The System Prompt (The Rules of the Game)
    # This is where we will eventually inject Saxo Bank's SOPs
    system_prompt = """You are the Chief Risk Officer (CRO) of a quantitative hedge fund.
    Your GOAL: Protect the capital. You have veto power over the CIO.
    
    RULES:
    1. MAX POSITION SIZE: No single stock can exceed 10% of the portfolio.
    2. STOP LOSS: We do not buy stocks with 'Negative' sentiment if technicals are also 'Bearish'.
    3. LOGIC CHECK: If the CIO's reasoning is vague or hallucinates data, REJECT IT.
    
    OUTPUT FORMAT:
    You must respond in strict JSON format with these keys:
    - "risk_score": (int) 0 to 10. (0 = Safe, 10 = Dangerous).
    - "approved": (bool) true or false.
    - "analysis": (str) A sharp, critical critique of the trade.
    """

    # 3. The User Prompt (The specific case)
    user_message = f"""
    PROPOSAL: {cio_proposal} for {ticker}
    CIO REASONING: {cio_logic}
    
    DATA CONTEXT:
    - Sentiment: {state.get('news_sentiment', 'Unknown')}
    - Technicals: {state.get('technical_analysis', 'Unknown')}
    - Fundamentals: {state.get('fundamental_analysis', 'Unknown')}
    """

    # 4. Invoke the AI
    # We ask for JSON output to make it machine-readable
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]
    
    # Note: In a real app, we would use structured output parsing. 
    # For now, we trust the model's intelligence.
    response = llm.invoke(messages)
    
    # 5. Parse the "Thought Process"
    # (Simple string parsing for this phase - we will upgrade this to Pydantic later)
    content = response.content
    
    # Fallback logic for the prototype
    approved = "true" in content.lower() and "risk_score" in content.lower()
    
    return {
        "risk_analysis": content,
        "risk_approved": approved,
        # We manually update the revision count if rejected
        "revision_count": state["revision_count"] + (0 if approved else 1)
    }