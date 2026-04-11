from datetime import date, datetime
from typing import Dict, List

from src.integrations.supabase_client import get_supabase_client

MAX_YEARS = 10
SELECT_COLUMNS = (
    "fiscal_year,"
    "period_end_date,"
    "filing_date,"
    "current_ratio,"
    "quick_ratio,"
    "gross_margin,"
    "operating_margin,"
    "net_margin,"
    "debt_to_assets_ratio,"
    "debt_to_equity,"
    "interest_coverage_ratio,"
    "asset_turnover,"
    "inventory_turnover,"
    "receivables_turnover,"
    "price_to_earnings,"
    "price_to_book,"
    "price_to_sales,"
    "price_to_free_cash_flow,"
    "enterprise_value_multiple,"
    "dividend_yield"
)


def _parse_as_of_date(as_of: str) -> str:
    value = (as_of or "").strip()
    if not value:
        raise ValueError("as_of is required")

    if "T" not in value:
        return date.fromisoformat(value).isoformat()

    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def _normalize_years(years: int) -> int:
    try:
        normalized_years = int(years)
    except (TypeError, ValueError) as exc:
        raise ValueError("years must be an integer") from exc

    if normalized_years < 1:
        raise ValueError("years must be at least 1")
    return min(normalized_years, MAX_YEARS)


def get_financial_ratios_history(
    ticker: str,
    as_of: str,
    years: int = MAX_YEARS,
) -> Dict[str, object]:
    """
    Return annual financial ratios for one ticker using only filings published on or before as_of.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must be a non-empty string")

    cutoff_date = _parse_as_of_date(as_of)
    limited_years = _normalize_years(years)
    supabase = get_supabase_client()

    response = (
        supabase.table("fundamental_ratios")
        .select(SELECT_COLUMNS)
        .eq("ticker", normalized_ticker)
        .eq("period_type", "FY")
        .lte("filing_date", cutoff_date)
        .order("filing_date", desc=True)
        .limit(limited_years)
        .execute()
    )
    rows = response.data or []

    return {
        "ticker": normalized_ticker,
        "as_of_date": cutoff_date,
        "years": limited_years,
        "periods": rows,
    }
