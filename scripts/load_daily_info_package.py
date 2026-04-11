#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

try:
    from src.integrations.daily_info_packages import load_all_daily_agent_packages, load_daily_agent_package
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.integrations.daily_info_packages import load_all_daily_agent_packages, load_daily_agent_package


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load prepared daily screening packages for one backtest trading date."
    )
    parser.add_argument("--package-date", required=True, help="Trading date in YYYY-MM-DD format")
    parser.add_argument(
        "--agent",
        choices=["technical", "fundamental", "news", "all"],
        default="all",
        help="Which agent package to load.",
    )
    parser.add_argument(
        "--ticker",
        help="Optional single-ticker filter for inspection. Omit this in normal backtest runs.",
    )
    parser.add_argument(
        "--simulation-mode",
        choices=["clean", "disinformation"],
        default="clean",
        help="Use clean or disinformation stock-news mode for the News Analyst package.",
    )
    parser.add_argument(
        "--disinformation-policy",
        choices=["append", "replace"],
        default="append",
        help="How manipulated stock news is merged when simulation mode is disinformation.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.agent == "all":
        payload = load_all_daily_agent_packages(
            args.package_date,
            ticker=args.ticker,
            simulation_mode=args.simulation_mode,
            disinformation_policy=args.disinformation_policy,
        )
    else:
        payload = load_daily_agent_package(
            args.agent,
            args.package_date,
            ticker=args.ticker,
            simulation_mode=args.simulation_mode,
            disinformation_policy=args.disinformation_policy,
        ).to_dict()

    print(json.dumps(payload, indent=args.indent, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
