#!/usr/bin/env python3
import argparse
import os
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from dotenv import load_dotenv
from supabase import Client, create_client

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build prepared daily stock packages from Supabase source tables."
    )
    parser.add_argument("--package-date", required=True, help="Trading date in YYYY-MM-DD format")
    parser.add_argument("--tickers", default=",".join(DOW_30_TICKERS))
    parser.add_argument("--technical-timeframe", default="1day")
    parser.add_argument("--technical-period-length", type=int, default=10)
    parser.add_argument("--db-batch-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_env() -> None:
    load_dotenv()


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) are required.")
    return create_client(supabase_url, supabase_key)


def chunked(values: Sequence[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt_value = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt_value = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def parse_iso_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def to_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return round(number, 4)


def pct_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous in (None, 0):
        return None
    return round(((current - previous) / previous) * 100, 2)


def diff(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current is None or previous is None:
        return None
    return round(current - previous, 4)


def isoformat_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def fetch_all(
    supabase: Client,
    table: str,
    tickers: Sequence[str],
    select_clause: str,
    date_column: Optional[str],
    start_value: Optional[str],
    end_value: Optional[str],
    extra_filters: Optional[List[tuple]] = None,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    extra_filters = extra_filters or []
    for ticker_chunk in chunked(list(tickers), 20):
        offset = 0
        while True:
            query = supabase.table(table).select(select_clause)
            query = query.in_("ticker", ticker_chunk)
            if date_column and start_value is not None:
                query = query.gte(date_column, start_value)
            if date_column and end_value is not None:
                query = query.lte(date_column, end_value)
            for filter_type, key, value in extra_filters:
                if filter_type == "eq":
                    query = query.eq(key, value)
                else:
                    raise ValueError(f"Unsupported filter type: {filter_type}")
            response = query.range(offset, offset + page_size - 1).execute()
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    return rows


def fetch_all_general_news(
    supabase: Client,
    start_value: str,
    end_value: str,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            supabase.table("general_news_daily")
            .select("id,title,content,published_at,publisher,site,dedupe_key")
            .gte("published_at", start_value)
            .lte("published_at", end_value)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def group_latest_two_by_ticker(rows: List[Dict[str, Any]], key_name: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ticker = row["ticker"]
        grouped[ticker].append(row)
    for ticker, ticker_rows in grouped.items():
        grouped[ticker] = sorted(ticker_rows, key=lambda row: row[key_name], reverse=True)
    return grouped


def compute_price_fields(current_row: Optional[Dict[str, Any]], previous_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not current_row:
        return {}

    price_open = to_float(current_row.get("price_open"))
    price_high = to_float(current_row.get("price_high"))
    price_low = to_float(current_row.get("price_low"))
    price_close = to_float(current_row.get("price_close"))
    prev_price_close = to_float(previous_row.get("price_close")) if previous_row else None

    return {
        "price_open": price_open,
        "price_high": price_high,
        "price_low": price_low,
        "price_close": price_close,
        "volume": current_row.get("volume"),
        "prev_price_close": prev_price_close,
        "chg_open_vs_prev_close": diff(price_open, prev_price_close),
        "chg_open_vs_prev_close_pct": pct_change(price_open, prev_price_close),
        "chg_close_vs_open": diff(price_close, price_open),
        "chg_close_vs_open_pct": pct_change(price_close, price_open),
        "chg_close_vs_prev_close": diff(price_close, prev_price_close),
        "chg_close_vs_prev_close_pct": pct_change(price_close, prev_price_close),
    }


def build_technical_row_index(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["ticker"]].append(row)
    for ticker, ticker_rows in grouped.items():
        grouped[ticker] = sorted(ticker_rows, key=lambda row: row["event_date"], reverse=True)
    return grouped


def compute_technical_fields(current_row: Optional[Dict[str, Any]], previous_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not current_row:
        return {
            "sma": None,
            "ema": None,
            "wma": None,
            "dema": None,
            "tema": None,
            "rsi": None,
            "standarddeviation": None,
            "williams": None,
            "adx": None,
            "chg_sma": None,
            "chg_ema": None,
            "chg_wma": None,
            "chg_dema": None,
            "chg_tema": None,
            "chg_rsi": None,
            "chg_standarddeviation": None,
            "chg_williams": None,
            "chg_adx": None,
        }

    result = {
        "sma": to_float(current_row.get("sma")),
        "ema": to_float(current_row.get("ema")),
        "wma": to_float(current_row.get("wma")),
        "dema": to_float(current_row.get("dema")),
        "tema": to_float(current_row.get("tema")),
        "rsi": to_float(current_row.get("rsi")),
        "standarddeviation": to_float(current_row.get("standarddeviation")),
        "williams": to_float(current_row.get("williams")),
        "adx": to_float(current_row.get("adx")),
    }
    if previous_row:
        result.update(
            {
                "chg_sma": diff(result["sma"], to_float(previous_row.get("sma"))),
                "chg_ema": diff(result["ema"], to_float(previous_row.get("ema"))),
                "chg_wma": diff(result["wma"], to_float(previous_row.get("wma"))),
                "chg_dema": diff(result["dema"], to_float(previous_row.get("dema"))),
                "chg_tema": diff(result["tema"], to_float(previous_row.get("tema"))),
                "chg_rsi": diff(result["rsi"], to_float(previous_row.get("rsi"))),
                "chg_standarddeviation": diff(
                    result["standarddeviation"],
                    to_float(previous_row.get("standarddeviation")),
                ),
                "chg_williams": diff(result["williams"], to_float(previous_row.get("williams"))),
                "chg_adx": diff(result["adx"], to_float(previous_row.get("adx"))),
            }
        )
    else:
        result.update(
            {
                "chg_sma": None,
                "chg_ema": None,
                "chg_wma": None,
                "chg_dema": None,
                "chg_tema": None,
                "chg_rsi": None,
                "chg_standarddeviation": None,
                "chg_williams": None,
                "chg_adx": None,
            }
        )
    return result


def build_fundamental_index(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["ticker"]].append(row)
    for ticker, ticker_rows in grouped.items():
        grouped[ticker] = sorted(
            ticker_rows,
            key=lambda row: (
                row.get("filing_date") or "",
                row.get("period_end_date") or "",
            ),
            reverse=True,
        )
    return grouped


def compute_fundamental_fields(
    current_row: Optional[Dict[str, Any]],
    previous_row: Optional[Dict[str, Any]],
    latest_filing: Optional[Dict[str, Any]],
    latest_inflation_row: Optional[Dict[str, Any]],
    package_date: date,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "fundamental_period_end_date": None,
        "fundamental_filing_date": None,
        "filing_flag": False,
        "filing_form": None,
        "inflation_rate": None,
    }

    if current_row:
        for field in (
            "current_ratio",
            "quick_ratio",
            "gross_margin",
            "operating_margin",
            "net_margin",
            "debt_to_assets_ratio",
            "debt_to_equity",
            "interest_coverage_ratio",
            "asset_turnover",
            "inventory_turnover",
            "receivables_turnover",
            "price_to_earnings",
            "price_to_book",
            "price_to_sales",
            "price_to_free_cash_flow",
            "enterprise_value_multiple",
            "dividend_yield",
        ):
            result[field] = to_float(current_row.get(field))

        result["fundamental_period_end_date"] = current_row.get("period_end_date")
        result["fundamental_filing_date"] = current_row.get("filing_date")
        prev_current_ratio = to_float(previous_row.get("current_ratio")) if previous_row else None
        prev_gross_margin = to_float(previous_row.get("gross_margin")) if previous_row else None
        prev_operating_margin = to_float(previous_row.get("operating_margin")) if previous_row else None
        prev_net_margin = to_float(previous_row.get("net_margin")) if previous_row else None
        prev_debt_to_equity = to_float(previous_row.get("debt_to_equity")) if previous_row else None

        result["prev_current_ratio"] = prev_current_ratio
        result["chg_current_ratio"] = diff(result.get("current_ratio"), prev_current_ratio)
        result["prev_gross_margin"] = prev_gross_margin
        result["chg_gross_margin"] = diff(result.get("gross_margin"), prev_gross_margin)
        result["prev_operating_margin"] = prev_operating_margin
        result["chg_operating_margin"] = diff(result.get("operating_margin"), prev_operating_margin)
        result["prev_net_margin"] = prev_net_margin
        result["chg_net_margin"] = diff(result.get("net_margin"), prev_net_margin)
        result["prev_debt_to_equity"] = prev_debt_to_equity
        result["chg_debt_to_equity"] = diff(result.get("debt_to_equity"), prev_debt_to_equity)

    if latest_filing and parse_iso_date(latest_filing.get("filing_date")) == package_date:
        result["filing_flag"] = True
        result["filing_form"] = latest_filing.get("form")

    if latest_inflation_row:
        result["inflation_rate"] = to_float(latest_inflation_row.get("value"))

    return result


def select_news_for_date(rows: List[Dict[str, Any]], package_date: date) -> Dict[str, Any]:
    rows_for_date: List[Dict[str, Any]] = []
    for row in rows:
        published_at = parse_iso_datetime(row.get("published_at"))
        if published_at and published_at.date() == package_date:
            row = dict(row)
            row["_published_at_dt"] = published_at
            rows_for_date.append(row)

    rows_for_date.sort(key=lambda row: row["_published_at_dt"], reverse=True)
    selected = rows_for_date[0] if rows_for_date else None
    return {
        "selected": selected,
        "count": len(rows_for_date),
    }


def compute_news_fields(
    stock_news_rows: List[Dict[str, Any]],
    general_news_rows: List[Dict[str, Any]],
    package_date: date,
) -> Dict[str, Any]:
    stock_news = select_news_for_date(stock_news_rows, package_date)
    general_news = select_news_for_date(general_news_rows, package_date)

    latest_stock = stock_news["selected"]
    latest_general = general_news["selected"]

    return {
        "latest_news_id": latest_stock.get("id") if latest_stock else None,
        "latest_news_title": latest_stock.get("title") if latest_stock else None,
        "latest_news_content": latest_stock.get("content") if latest_stock else None,
        "latest_news_published_at": isoformat_or_none(latest_stock.get("_published_at_dt")) if latest_stock else None,
        "daily_news_count": stock_news["count"],
        "latest_general_news_id": latest_general.get("id") if latest_general else None,
        "latest_general_news_title": latest_general.get("title") if latest_general else None,
        "latest_general_news_content": latest_general.get("content") if latest_general else None,
        "latest_general_news_published_at": isoformat_or_none(latest_general.get("_published_at_dt")) if latest_general else None,
        "daily_general_news_count": general_news["count"],
    }


def build_source_refs(
    current_price_row: Optional[Dict[str, Any]],
    current_technical_row: Optional[Dict[str, Any]],
    current_fundamental_row: Optional[Dict[str, Any]],
    latest_news_id: Optional[int],
    latest_general_news_id: Optional[int],
    latest_filing: Optional[Dict[str, Any]],
    latest_inflation_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    refs: Dict[str, Any] = {}
    if current_price_row:
        refs["market_prices_daily"] = current_price_row.get("id")
    if current_technical_row:
        refs["technical_indicators_daily"] = current_technical_row.get("id")
    if current_fundamental_row:
        refs["fundamental_ratios"] = current_fundamental_row.get("id")
    if latest_news_id is not None:
        refs["stock_news_daily"] = latest_news_id
    if latest_general_news_id is not None:
        refs["general_news_daily"] = latest_general_news_id
    if latest_filing:
        refs["sec_filing_events"] = latest_filing.get("id")
    if latest_inflation_row:
        refs["economic_indicators"] = latest_inflation_row.get("id")
    return refs


def upsert_rows(supabase: Client, rows: List[Dict[str, Any]], db_batch_size: int) -> None:
    for batch_start in range(0, len(rows), db_batch_size):
        batch = rows[batch_start : batch_start + db_batch_size]
        (
            supabase.table("daily_stock_packages")
            .upsert(
                batch,
                on_conflict="package_date,ticker",
            )
            .execute()
        )


def normalize_indicator_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace(" ", "").replace("_", "")


def select_latest_inflation_row(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    inflation_names = {"inflation", "inflationrate"}
    inflation_rows = [
        row for row in rows if normalize_indicator_name(row.get("indicator_name")) in inflation_names
    ]
    if not inflation_rows:
        return None
    return sorted(inflation_rows, key=lambda row: row.get("event_date") or "", reverse=True)[0]


def main() -> None:
    args = parse_args()
    load_env()
    supabase = get_supabase_client()

    package_date = parse_date_arg(args.package_date)
    cutoff_dt = datetime.combine(package_date, time.max, tzinfo=timezone.utc)
    package_start_dt = datetime.combine(package_date, time.min, tzinfo=timezone.utc)
    cutoff_iso = cutoff_dt.isoformat()
    package_start_iso = package_start_dt.isoformat()
    lookback_start_date = package_date - timedelta(days=10)
    lookback_start_iso = datetime.combine(lookback_start_date, time.min, tzinfo=timezone.utc).isoformat()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]

    market_rows = fetch_all(
        supabase,
        table="market_prices_daily",
        tickers=tickers,
        select_clause="id,ticker,event_timestamp,price_open,price_high,price_low,price_close,volume",
        date_column="event_timestamp",
        start_value=lookback_start_iso,
        end_value=cutoff_iso,
    )
    technical_rows = fetch_all(
        supabase,
        table="technical_indicators_daily",
        tickers=tickers,
        select_clause="id,ticker,timeframe,period_length,event_date,sma,ema,wma,dema,tema,rsi,standarddeviation,williams,adx",
        date_column="event_date",
        start_value=lookback_start_date.isoformat(),
        end_value=package_date.isoformat(),
        extra_filters=[
            ("eq", "timeframe", args.technical_timeframe),
            ("eq", "period_length", args.technical_period_length),
        ],
    )
    fundamental_rows = fetch_all(
        supabase,
        table="fundamental_ratios",
        tickers=tickers,
        select_clause=(
            "id,ticker,period_end_date,filing_date,current_ratio,quick_ratio,gross_margin,operating_margin,net_margin,"
            "debt_to_assets_ratio,debt_to_equity,interest_coverage_ratio,asset_turnover,inventory_turnover,"
            "receivables_turnover,price_to_earnings,price_to_book,"
            "price_to_sales,price_to_free_cash_flow,enterprise_value_multiple,dividend_yield"
        ),
        date_column="filing_date",
        start_value=None,
        end_value=package_date.isoformat(),
    )
    filing_rows = fetch_all(
        supabase,
        table="sec_filing_events",
        tickers=tickers,
        select_clause="id,ticker,form,filing_date,acceptance_datetime",
        date_column="filing_date",
        start_value=None,
        end_value=package_date.isoformat(),
    )
    stock_news_rows = fetch_all(
        supabase,
        table="stock_news_daily",
        tickers=tickers,
        select_clause="id,ticker,title,content,published_at,publisher,site,dedupe_key",
        date_column="published_at",
        start_value=package_start_iso,
        end_value=cutoff_iso,
    )
    general_news_rows = fetch_all_general_news(supabase, package_start_iso, cutoff_iso)
    macro_rows_response = (
        supabase.table("economic_indicators")
        .select("id,indicator_name,event_date,value")
        .lte("event_date", package_date.isoformat())
        .eq("country", "US")
        .execute()
    )
    macro_rows = macro_rows_response.data or []

    market_by_ticker = group_latest_two_by_ticker(market_rows, "event_timestamp")
    technical_by_ticker = build_technical_row_index(technical_rows)
    fundamental_by_ticker = build_fundamental_index(fundamental_rows)
    filing_by_ticker = group_latest_two_by_ticker(filing_rows, "filing_date")

    stock_news_by_ticker: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in stock_news_rows:
        stock_news_by_ticker[row["ticker"]].append(row)

    macro_rows_sorted = sorted(
        macro_rows,
        key=lambda row: (row.get("event_date") or "", row.get("indicator_name") or ""),
        reverse=True,
    )
    latest_inflation_row = select_latest_inflation_row(macro_rows_sorted)

    package_rows: List[Dict[str, Any]] = []
    for ticker in tickers:
        market_candidates = market_by_ticker.get(ticker, [])
        current_market = None
        previous_market = None
        for candidate in market_candidates:
            event_dt = parse_iso_datetime(candidate.get("event_timestamp"))
            if not event_dt:
                continue
            if event_dt.date() == package_date and current_market is None:
                current_market = candidate
            elif event_dt.date() < package_date and previous_market is None:
                previous_market = candidate
            if current_market and previous_market:
                break

        technical_candidates = technical_by_ticker.get(ticker, [])
        current_technical = None
        previous_technical = None
        for candidate in technical_candidates:
            event_date = parse_iso_date(candidate.get("event_date"))
            if event_date == package_date and current_technical is None:
                current_technical = candidate
            elif event_date and event_date < package_date and previous_technical is None:
                previous_technical = candidate
            if current_technical and previous_technical:
                break

        fundamental_candidates = fundamental_by_ticker.get(ticker, [])
        current_fundamental = fundamental_candidates[0] if fundamental_candidates else None
        previous_fundamental = fundamental_candidates[1] if len(fundamental_candidates) > 1 else None

        filing_candidates = filing_by_ticker.get(ticker, [])
        latest_filing = filing_candidates[0] if filing_candidates else None

        price_fields = compute_price_fields(current_market, previous_market)
        technical_fields = compute_technical_fields(current_technical, previous_technical)
        fundamental_fields = compute_fundamental_fields(
            current_fundamental,
            previous_fundamental,
            latest_filing,
            latest_inflation_row,
            package_date,
        )
        news_fields = compute_news_fields(
            stock_news_by_ticker.get(ticker, []),
            general_news_rows,
            package_date,
        )

        package_row: Dict[str, Any] = {
            "package_date": package_date.isoformat(),
            "ticker": ticker,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        package_row.update(price_fields)
        package_row.update(technical_fields)
        package_row.update(fundamental_fields)
        package_row.update(news_fields)
        package_row["source_refs"] = build_source_refs(
            current_market,
            current_technical,
            current_fundamental,
            news_fields.get("latest_news_id"),
            news_fields.get("latest_general_news_id"),
            latest_filing,
            latest_inflation_row,
        )
        package_rows.append(package_row)

    if args.dry_run:
        print(f"Built {len(package_rows)} package rows for {package_date.isoformat()} (dry run).")
        for sample in package_rows[:3]:
            print(
                sample["ticker"],
                {
                    "price_close": sample.get("price_close"),
                    "daily_news_count": sample.get("daily_news_count"),
                    "filing_flag": sample.get("filing_flag"),
                    "latest_news_id": sample.get("latest_news_id"),
                    "inflation_rate": sample.get("inflation_rate"),
                },
            )
        return

    upsert_rows(supabase, package_rows, args.db_batch_size)
    print(
        f"Upserted {len(package_rows)} rows into daily_stock_packages "
        f"for {package_date.isoformat()}."
    )


if __name__ == "__main__":
    main()
