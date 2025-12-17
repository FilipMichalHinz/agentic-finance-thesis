import sys
import os
import time
from uuid import uuid4
from dotenv import load_dotenv
from termcolor import colored
from src.integrations.supabase_logger import SupabaseLogger
from src.integrations.alpaca_client import AlpacaPaperBroker

# --- 1. SETUP ENVIRONMENT ---
# Load environment variables (API Keys) from .env file
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    print(colored("CRITICAL ERROR: GOOGLE_API_KEY not found in environment!", "red"))
    print("Please check your .env file.")
    sys.exit(1)
# Add the current directory to Python's path so it can find the 'src' folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- 2. IMPORTS ---
# We import these AFTER setting up the path
from src.graph import app

# --- 2b. OPTIONAL INTEGRATIONS ---
RUN_ID = os.getenv("RUN_ID") or str(uuid4())
supabase_logger = SupabaseLogger()
alpaca_broker = AlpacaPaperBroker()

# Helper to send each agent update to Supabase without coupling to the graph
def log_update_to_supabase(run_id, update):
    if not supabase_logger.enabled:
        return
    for agent_name, state_data in update.items():
        supabase_logger.log_event(
            run_id=run_id,
            agent=agent_name,
            stage="completed",
            payload=state_data,
        )

# --- 3. HELPER FUNCTIONS ---
def print_update(update):
    """
    Helper to visualize the agent conversation in the terminal.
    """
    for agent_name, state_data in update.items():
        # Header for the agent
        print(colored(f"\n--- {agent_name.upper()} FINISHED ---", "cyan"))
        
        # Specific print logic for each agent type
        if agent_name == "technical_analyst":
            print(f"Signals: {state_data.get('technical_analysis')}")
            
        elif agent_name == "sentiment_analyst":
            print(f"Sentiment: {state_data.get('sentiment_analysis')}")
            
        elif agent_name == "fundamental_analyst":
            print(f"Analysis: {state_data.get('fundamental_analysis')}")
            
        elif agent_name == "cio":
            print(colored(f"Proposal: {state_data.get('cio_portfolio_allocation')}", "blue"))
            print(f"Reasoning: {state_data.get('cio_reasoning')}")
            
        elif agent_name == "risk_manager":
            approved = state_data.get('risk_approved')
            color = "green" if approved else "red"
            print(colored(f"Decision: {'APPROVED' if approved else 'REJECTED'}", color, attrs=['bold']))
            print(f"Feedback: {state_data.get('risk_analysis')}")

# --- 4. MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    print(colored("Starting Hedge Fund Simulation...", "yellow"))
    
    # Initialize the "Project Folder" with a ticker
    initial_state = {
        "ticker": "TSLA",  # Change this to AAPL, NVDA, etc.
        "revision_count": 0,
        "messages": []
    }
    
    try:
        # Run the Graph
        # app.stream executes the nodes one by one
        for update in app.stream(initial_state):
            print_update(update)
            log_update_to_supabase(RUN_ID, update)
            # Add a tiny sleep so the logs don't fly by too fast
            time.sleep(1)

        # Optional: show Alpaca account summary to confirm connectivity
        if alpaca_broker.enabled:
            account = alpaca_broker.get_account_summary()
            if account:
                print(colored(f"\nAlpaca Paper Account: {account}", "magenta"))
            
    except Exception as e:
        print(colored(f"Crash detected: {e}", "red"))
        
    print(colored("\nSimulation Complete.", "yellow"))
