import sys
import os
from uuid import uuid4
from dotenv import load_dotenv
from termcolor import colored
from src.integrations.google_genai import resolve_google_genai_settings

# --- 1. SETUP ENVIRONMENT ---
# Load environment variables (API Keys) from .env file
# Prefer repo-local settings over any unrelated Google env vars already in the shell.
load_dotenv(override=True)
try:
    resolve_google_genai_settings()
except RuntimeError as exc:
    print(colored(f"CRITICAL ERROR: {exc}", "red"))
    print("Please check your .env file.")
    sys.exit(1)
# Add the current directory to Python's path so it can find the 'src' folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- 2. IMPORTS ---
# We import these AFTER setting up the path
from src.graph import app

# --- 3. HELPER FUNCTIONS ---
def print_update(update):
    """
    Print short, readable summaries of the baseline workflow steps.
    """
    for agent_name, state_data in update.items():
        print(colored(f"\n--- {agent_name.upper()} FINISHED ---", "cyan"))
        if agent_name == "load_baseline_inputs":
            packages = state_data.get("daily_packages", {})
            package_date = state_data.get("package_date")
            current_portfolio = state_data.get("current_portfolio", {})
            print(f"Package date: {package_date}")
            print(
                "Loaded package counts: "
                f"technical={packages.get('technical', {}).get('stock_count', 0)}, "
                f"news={packages.get('news', {}).get('stock_count', 0)}, "
                f"fundamental={packages.get('fundamental', {}).get('stock_count', 0)}"
            )
            print(
                "Current portfolio: "
                f"holdings={current_portfolio.get('holdings_count', 0)}, "
                f"cash_weight={current_portfolio.get('cash_weight', 0):.2%}"
            )
        elif agent_name in {"technical_screen", "news_screen", "fundamental_screen"}:
            key = next(iter(state_data))
            flagged = [row["ticker"] for row in state_data.get(key, []) if row.get("status") == "flag_for_deep_analysis"]
            print(f"Flagged tickers ({len(flagged)}): {', '.join(flagged[:10]) if flagged else 'none'}")
        elif agent_name == "build_shared_deep_analysis_set":
            deep_set = state_data.get("shared_deep_analysis_set", [])
            print(f"Shared deep-analysis set ({len(deep_set)}): {', '.join(deep_set) if deep_set else 'none'}")
        elif agent_name == "technical_deep_analysis":
            print(state_data.get("technical_report"))
        elif agent_name == "news_deep_analysis":
            print(state_data.get("news_report"))
        elif agent_name == "fundamental_deep_analysis":
            print(state_data.get("fundamental_report"))
        elif agent_name == "portfolio_manager":
            decision = state_data.get("portfolio_decision", {})
            print(colored(decision.get("summary", ""), "blue"))
            print(f"Target weights: {decision.get('target_weights', {})}")
        elif agent_name == "build_trade_preview":
            preview = state_data.get("trade_preview", {})
            print(f"IPS status: {preview.get('ips_status')}")
            print(f"Actions: {preview.get('actions', [])}")

# --- 4. MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    print(colored("Starting Baseline Portfolio Workflow...", "yellow"))

    # The baseline keeps the entry inputs small and explicit.
    initial_state = {
        "run_id": os.getenv("RUN_ID") or str(uuid4()),
        "requested_package_date": os.getenv("PACKAGE_DATE") or os.getenv("SIM_TIME"),
        "initial_cash": float(os.getenv("INITIAL_CASH", "100000")),
        "simulation_mode": os.getenv("SIMULATION_MODE", "clean"),
        "disinformation_policy": os.getenv("DISINFORMATION_POLICY", "append"),
        "messages": [],
    }

    try:
        for update in app.stream(initial_state):
            print_update(update)
    except Exception as e:
        print(colored(f"Crash detected: {e}", "red"))

    print(colored("\nBaseline Workflow Complete.", "yellow"))
