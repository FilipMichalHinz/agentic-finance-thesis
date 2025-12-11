from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.agents.technical_analyst import technical_analyst_node
from src.agents.sentiment_analyst import sentiment_analyst_node
from src.agents.fundamental_analyst import fundamental_analyst_node
from src.agents.cio import cio_agent_node
from src.agents.risk_manager import risk_manager_node

def risk_decision_path(state: AgentState):
    if state["risk_approved"]:
        return "approved"
    if state["revision_count"] >= 3:
        return "too_many_retries"
    return "rejected"

workflow = StateGraph(AgentState)

# --- ADD NODES ---
workflow.add_node("technical_analyst", technical_analyst_node)
workflow.add_node("sentiment_analyst", sentiment_analyst_node)
workflow.add_node("fundamental_analyst", fundamental_analyst_node)
workflow.add_node("cio", cio_agent_node)
workflow.add_node("risk_manager", risk_manager_node)

# --- SET ENTRY POINT ---
workflow.set_entry_point("technical_analyst")

# --- DEFINE EDGES (The Assembly Line) ---
# 1. Gather all data sequentially
workflow.add_edge("technical_analyst", "sentiment_analyst")
workflow.add_edge("sentiment_analyst", "fundamental_analyst")
workflow.add_edge("fundamental_analyst", "cio")

# 2. CIO Proposes -> Risk Manager Reviews
workflow.add_edge("cio", "risk_manager")

# 3. Risk Loop
workflow.add_conditional_edges(
    "risk_manager",
    risk_decision_path,
    {
        "approved": END,
        "rejected": "cio",      # Feedback Loop
        "too_many_retries": END
    }
)

app = workflow.compile()