#!/usr/bin/env python3
import argparse
import json
import os
import random
import socket
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from supabase import Client, create_client

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS

FMP_BASE = "https://financialmodelingprep.com/stable"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
DEFAULT_PERIODS = ["annual"]

NUMERIC_FIELD_MAPPINGS = {
    "gross_margin": ["grossProfitMargin", "grossMargin"],
    "ebit_margin": ["ebitMargin"],
    "ebitda_margin": ["ebitdaMargin"],
    "operating_margin": ["operatingProfitMargin", "operatingMargin"],
    "pretax_margin": ["pretaxProfitMargin"],
    "continuous_operations_profit_margin": ["continuousOperationsProfitMargin"],
    "net_margin": ["netProfitMargin", "netMargin"],
    "bottom_line_profit_margin": ["bottomLineProfitMargin"],
    "receivables_turnover": ["receivablesTurnover"],
    "payables_turnover": ["payablesTurnover"],
    "inventory_turnover": ["inventoryTurnover"],
    "fixed_asset_turnover": ["fixedAssetTurnover"],
    "asset_turnover": ["assetTurnover"],
    "current_ratio": ["currentRatio"],
    "quick_ratio": ["quickRatio"],
    "solvency_ratio": ["solvencyRatio"],
    "cash_ratio": ["cashRatio"],
    "price_to_earnings": ["priceToEarningsRatio", "priceEarningsRatio"],
    "price_to_earnings_growth_ratio": ["priceToEarningsGrowthRatio", "priceEarningsToGrowthRatio", "pegRatio"],
    "forward_price_to_earnings_growth_ratio": ["forwardPriceToEarningsGrowthRatio"],
    "price_earnings_to_growth": ["priceToEarningsGrowthRatio", "priceEarningsToGrowthRatio", "pegRatio"],
    "price_to_book": ["priceToBookRatio", "priceBookValueRatio"],
    "price_to_sales": ["priceToSalesRatio"],
    "price_to_free_cash_flow": ["priceToFreeCashFlowRatio", "priceToFreeCashFlowsRatio"],
    "price_to_operating_cash_flow": ["priceToOperatingCashFlowRatio", "priceCashFlowRatio"],
    "price_to_cash_flow": ["priceToOperatingCashFlowRatio", "priceCashFlowRatio"],
    "debt_to_assets_ratio": ["debtToAssetsRatio", "debtRatio"],
    "debt_ratio": ["debtToAssetsRatio", "debtRatio"],
    "debt_to_equity": ["debtToEquityRatio", "debtEquityRatio", "debtToEquity"],
    "debt_to_capital_ratio": ["debtToCapitalRatio"],
    "long_term_debt_to_capital_ratio": ["longTermDebtToCapitalRatio"],
    "financial_leverage_ratio": ["financialLeverageRatio"],
    "working_capital_turnover_ratio": ["workingCapitalTurnoverRatio"],
    "operating_cash_flow_ratio": ["operatingCashFlowRatio"],
    "operating_cash_flow_sales_ratio": ["operatingCashFlowSalesRatio"],
    "free_cash_flow_operating_cash_flow_ratio": ["freeCashFlowOperatingCashFlowRatio"],
    "debt_service_coverage_ratio": ["debtServiceCoverageRatio"],
    "interest_coverage_ratio": ["interestCoverageRatio", "interestCoverage"],
    "interest_coverage": ["interestCoverageRatio", "interestCoverage"],
    "short_term_operating_cash_flow_coverage_ratio": ["shortTermOperatingCashFlowCoverageRatio"],
    "operating_cash_flow_coverage_ratio": ["operatingCashFlowCoverageRatio"],
    "capital_expenditure_coverage_ratio": ["capitalExpenditureCoverageRatio"],
    "dividend_paid_and_capex_coverage_ratio": ["dividendPaidAndCapexCoverageRatio"],
    "dividend_payout_ratio": ["dividendPayoutRatio"],
    "dividend_yield": ["dividendYield"],
    "dividend_yield_percentage": ["dividendYieldPercentage"],
    "revenue_per_share": ["revenuePerShare"],
    "net_income_per_share": ["netIncomePerShare"],
    "interest_debt_per_share": ["interestDebtPerShare"],
    "cash_per_share": ["cashPerShare"],
    "book_value_per_share": ["bookValuePerShare"],
    "tangible_book_value_per_share": ["tangibleBookValuePerShare"],
    "shareholders_equity_per_share": ["shareholdersEquityPerShare"],
    "operating_cash_flow_per_share": ["operatingCashFlowPerShare"],
    "capex_per_share": ["capexPerShare"],
    "free_cash_flow_per_share": ["freeCashFlowPerShare"],
    "net_income_per_ebt": ["netIncomePerEBT"],
    "ebt_per_ebit": ["ebtPerEbit"],
    "price_to_fair_value": ["priceToFairValue"],
    "debt_to_market_cap": ["debtToMarketCap"],
    "effective_tax_rate": ["effectiveTaxRate"],
    "return_on_assets": ["returnOnAssets"],
    "return_on_equity": ["returnOnEquity"],
    "return_on_capital_employed": ["returnOnCapitalEmployed"],
    "enterprise_value_multiple": ["enterpriseValueMultiple"],
}


class FmpAccessError(RuntimeError):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest FMP ratios into fundamental_ratios")
    parser.add_argument("--tickers", default=",".join(DOW_30_TICKERS))
    parser.add_argument("--periods", default=",".join(DEFAULT_PERIODS), help="Comma-separated: annual,quarter")
    parser.add_argument("--limit", type=int, default=12, help="Historical periods per ticker")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--db-batch-size", type=int, default=200)
    parser.add_argument("--api-key", default=os.getenv("FMP_API_KEY") or os.getenv("FINANCIAL_MODELING_PREP_API_KEY"))
    return parser.parse_args()


def fetch_json(url, api_key, sleep_seconds=0.2, timeout_seconds=30.0, max_retries=5, retry_backoff_seconds=2.0):
    req = Request(url, headers={"User-Agent": "agentic-finance-thesis/1.0"})
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(req, timeout=timeout_seconds) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            time.sleep(sleep_seconds)
            return payload
        except HTTPError as e:
            last_error = e
            response_body = ""
            try:
                response_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                response_body = ""
            if e.code == 402:
                raise FmpAccessError(
                    "FMP returned 402 Payment Required for the ratios endpoint. "
                    "The request is reaching FMP, but this period/endpoint combination likely is not included in your current plan. "
                    "If you are on FMP Starter, try --periods annual."
                ) from e
            if e.code == 403:
                raise FmpAccessError(
                    "FMP returned 403 for the ratios endpoint. Check that your API key is valid and is being sent correctly."
                ) from e
            if e.code not in RETRYABLE_STATUS_CODES or attempt == max_retries:
                break
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(
                f"⚠️  HTTP {e.code} fetching {url} "
                f"(attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
        except (URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                break
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(
                f"⚠️  Network/error fetching {url}: {e} "
                f"(attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def build_url(endpoint, symbol, period, limit, api_key):
    query = urlencode({
        "symbol": symbol,
        "period": period,
        "limit": limit,
        "apikey": api_key,
    })
    return f"{FMP_BASE}/{endpoint}?{query}"


def parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value):
    if not value:
        return None
    candidate = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(value), fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def parse_numeric(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def sanitize_json(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): sanitize_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_json(v) for v in value]
    number = parse_numeric(value)
    if number is not None:
        return number
    return str(value)


def first_numeric(sample, keys):
    for key in keys:
        if key in sample:
            number = parse_numeric(sample.get(key))
            if number is not None:
                return number
    return None


def canonical_period_label(raw_period):
    raw_period = (raw_period or "").upper()
    if raw_period == "FY":
        return "FY", None
    if raw_period.startswith("Q") and len(raw_period) == 2 and raw_period[1].isdigit():
        return "Q", int(raw_period[1])
    if raw_period == "ANNUAL":
        return "FY", None
    if raw_period == "QUARTER":
        return "Q", None
    return raw_period or "UNKNOWN", None


def calendar_quarter_from_date(period_end_date):
    if period_end_date is None:
        return None
    return ((period_end_date.month - 1) // 3) + 1


def build_source_period_key(period_type, period_end_date, filing_date, fiscal_year, fiscal_quarter):
    return "|".join([
        period_type or "",
        period_end_date or "",
        filing_date or "",
        str(fiscal_year or ""),
        str(fiscal_quarter or ""),
    ])


def fetch_ratios_rows(ticker, period, api_key, args):
    url = build_url("ratios", ticker, period, args.limit, api_key)
    payload = fetch_json(
        url,
        api_key=api_key,
        sleep_seconds=args.sleep_seconds,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    if isinstance(payload, dict):
        return [payload]
    return payload or []


def build_row(ticker, sample):
    if sample is None:
        return None

    period_end = parse_date(sample.get("date"))
    if period_end is None:
        return None

    period_type, fiscal_quarter = canonical_period_label(sample.get("period"))
    fiscal_year = sample.get("fiscalYear")
    try:
        fiscal_year = int(fiscal_year) if fiscal_year not in (None, "") else None
    except (TypeError, ValueError):
        fiscal_year = None

    filing_date = parse_date(sample.get("filingDate") or sample.get("fillingDate"))
    available_at = parse_datetime(sample.get("acceptedDate"))
    company_name = sample.get("companyName") or sample.get("name")
    calendar_year = period_end.year
    calendar_quarter = calendar_quarter_from_date(period_end)
    source_period_key = build_source_period_key(
        period_type=period_type,
        period_end_date=period_end.isoformat(),
        filing_date=filing_date.isoformat() if filing_date else "",
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
    )

    row = {
        "provider": "fmp",
        "ticker": ticker,
        "company_name": company_name,
        "source_period_key": source_period_key,
        "period_type": period_type,
        "period_end_date": period_end.isoformat(),
        "filing_date": filing_date.isoformat() if filing_date else None,
        "available_at": available_at,
        "reported_currency": sample.get("reportedCurrency"),
        "fiscal_year": fiscal_year,
        "fiscal_quarter": fiscal_quarter,
        "calendar_year": calendar_year,
        "calendar_quarter": calendar_quarter,
        "raw_payload": sanitize_json(sample),
    }
    for column, keys in NUMERIC_FIELD_MAPPINGS.items():
        row[column] = first_numeric(sample, keys)
    return row


def flush_batch(supabase: Client, rows):
    if not rows:
        return
    supabase.table("fundamental_ratios").upsert(
        rows,
        on_conflict="provider,ticker,source_period_key",
    ).execute()


def main():
    load_dotenv()
    args = parse_args()

    if not args.api_key:
        raise SystemExit("Set FMP_API_KEY or FINANCIAL_MODELING_PREP_API_KEY, or pass --api-key")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    periods = [period.strip().lower() for period in args.periods.split(",") if period.strip()]
    unsupported = [period for period in periods if period not in {"quarter", "annual"}]
    if unsupported:
        raise SystemExit(f"Unsupported --periods values: {', '.join(unsupported)}")

    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    supabase: Client = create_client(supabase_url, supabase_key)

    print("🚀 Starting FMP ratios ingestion...")
    print(f" Tracking {len(tickers)} tickers across periods {','.join(periods)}...")

    pending_rows = []
    total_rows = 0
    for ticker in tickers:
        print(f" Downloading FMP ratios for {ticker}...")
        try:
            bundle_rows = []
            for period in periods:
                ratios_rows = fetch_ratios_rows(ticker, period, args.api_key, args)
                for sample in ratios_rows:
                    row = build_row(ticker, sample)
                    if row is not None:
                        bundle_rows.append(row)
        except FmpAccessError as e:
            raise SystemExit(str(e)) from e
        except Exception as e:
            print(f"   ❌ Failed to process {ticker}: {e}")
            continue

        if not bundle_rows:
            print(f"   ⚠️ No FMP rows found for {ticker}")
            continue

        pending_rows.extend(bundle_rows)
        total_rows += len(bundle_rows)
        print(f"   ✅ Prepared {len(bundle_rows)} rows for {ticker}")

        if len(pending_rows) >= args.db_batch_size:
            flush_batch(supabase, pending_rows)
            print(f"   ↳ Upserted {len(pending_rows)} rows")
            pending_rows = []

    flush_batch(supabase, pending_rows)
    if pending_rows:
        print(f"   ↳ Upserted {len(pending_rows)} rows")

    print(f"🏁 FMP ratios ingestion complete. Prepared {total_rows} rows.")


if __name__ == "__main__":
    main()
