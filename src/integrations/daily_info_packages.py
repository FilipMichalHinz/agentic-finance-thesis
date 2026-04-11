import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from supabase import Client, create_client
from src.integrations.stock_news import build_daily_news_package_fields_for_date

AgentName = Literal["technical", "fundamental", "news"]

_SUPABASE_CLIENT: Optional[Client] = None


@dataclass
class DailyAgentPackage:
    """
    Backtest-safe screening package for a single agent on a single trading day.

    The package loader reads only the prepared day-specific Supabase views and
    never falls back to raw source tables or live APIs. This keeps runtime
    retrieval bounded to the exact trading date requested by the backtest loop.
    """

    agent: AgentName
    package_date: str
    stocks: List[Dict[str, Any]]
    shared_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["stock_count"] = len(self.stocks)
        return payload


def _get_supabase_client() -> Client:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY")
        _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT


def _fetch_view_rows(
    view_name: str,
    package_date: str,
    *,
    ticker: Optional[str] = None,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Return only rows for the requested trading date from a prepared screening view.
    """

    supabase = _get_supabase_client()
    rows: List[Dict[str, Any]] = []
    offset = 0

    while True:
        query = (
            supabase.table(view_name)
            .select("*")
            .eq("package_date", package_date)
            .range(offset, offset + page_size - 1)
        )
        if ticker:
            query = query.eq("ticker", ticker)

        response = query.execute()
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    if rows and "ticker" in rows[0]:
        rows = sorted(rows, key=lambda row: row["ticker"])
    return rows


def _fetch_single_context_row(view_name: str, package_date: str) -> Optional[Dict[str, Any]]:
    rows = _fetch_view_rows(view_name, package_date)
    if not rows:
        return None
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected one shared-context row in {view_name} for {package_date}, found {len(rows)}."
        )
    return rows[0]


def get_latest_available_package_date() -> Optional[str]:
    """
    Return the most recent package date present in the prepared screening views.

    We use the technical view as the reference because every baseline run needs it
    and it is populated per-stock like the other two screening views.
    """

    supabase = _get_supabase_client()
    response = (
        supabase.table("daily_technical_analyst_screening_view")
        .select("package_date")
        .order("package_date", desc=True)
        .limit(100)
        .execute()
    )
    rows = response.data or []
    seen = []
    for row in rows:
        package_date = row.get("package_date")
        if package_date and package_date not in seen:
            seen.append(package_date)
    return seen[0] if seen else None


def load_daily_agent_package(
    agent: AgentName,
    package_date: str,
    *,
    ticker: Optional[str] = None,
    simulation_mode: Optional[str] = None,
    disinformation_policy: Optional[str] = None,
) -> DailyAgentPackage:
    """
    Load the exact screening package for one agent on one trading date.

    This is the runtime boundary the backtest loop should call. By forcing an
    explicit package_date and reading only the prepared views, the agents cannot
    accidentally see other days or raw future data.
    """

    if agent == "technical":
        return DailyAgentPackage(
            agent=agent,
            package_date=package_date,
            stocks=_fetch_view_rows("daily_technical_analyst_screening_view", package_date, ticker=ticker),
        )

    if agent == "fundamental":
        return DailyAgentPackage(
            agent=agent,
            package_date=package_date,
            stocks=_fetch_view_rows("daily_fundamental_analyst_screening_view", package_date, ticker=ticker),
            shared_context=_fetch_single_context_row("daily_fundamental_shared_context_view", package_date),
        )

    if agent == "news":
        stock_rows = _fetch_view_rows("daily_news_analyst_screening_view", package_date, ticker=ticker)
        if simulation_mode and simulation_mode.strip().lower() not in {"", "clean", "baseline", "normal"}:
            news_fields_by_ticker = build_daily_news_package_fields_for_date(
                package_date,
                simulation_mode=simulation_mode,
                disinformation_policy=disinformation_policy,
            )
            for row in stock_rows:
                merged_fields = news_fields_by_ticker.get(row["ticker"])
                if merged_fields:
                    row["latest_news_id"] = merged_fields["latest_news_id"]
                    row["latest_news_title"] = merged_fields["latest_news_title"]
                    row["daily_news_count"] = merged_fields["daily_news_count"]
        return DailyAgentPackage(
            agent=agent,
            package_date=package_date,
            stocks=stock_rows,
            shared_context=_fetch_single_context_row("daily_news_shared_context_view", package_date),
        )

    raise ValueError(f"Unsupported agent: {agent}")


def load_all_daily_agent_packages(
    package_date: str,
    *,
    ticker: Optional[str] = None,
    simulation_mode: Optional[str] = None,
    disinformation_policy: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Convenience wrapper for one full daily screening cycle.
    """

    return {
        "technical": load_daily_agent_package("technical", package_date, ticker=ticker).to_dict(),
        "fundamental": load_daily_agent_package("fundamental", package_date, ticker=ticker).to_dict(),
        "news": load_daily_agent_package(
            "news",
            package_date,
            ticker=ticker,
            simulation_mode=simulation_mode,
            disinformation_policy=disinformation_policy,
        ).to_dict(),
    }
