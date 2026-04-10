import argparse
import hashlib
import os
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

FMP_BASE_URL = "https://financialmodelingprep.com/stable"


def default_start_date() -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()


def default_end_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest FMP market news into Supabase")
    parser.add_argument("--tickers", default="NVDA", help="Comma-separated tickers for stock news")
    parser.add_argument("--start-date", default=default_start_date(), help="Inclusive start date, format YYYY-MM-DD")
    parser.add_argument("--end-date", default=default_end_date(), help="Inclusive end date, format YYYY-MM-DD")
    parser.add_argument(
        "--news-types",
        default="stock_news,general_news",
        help="Comma-separated set of stock_news,general_news",
    )
    parser.add_argument("--page-size", type=int, default=50, help="Page size for latest-feed endpoints")
    parser.add_argument("--general-pages", type=int, default=5, help="How many general-news pages to scan")
    parser.add_argument("--max-stock-news-per-day", type=int, default=10)
    parser.add_argument("--max-general-news-per-day", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print counts without writing to Supabase")
    return parser.parse_args()


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def normalize_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    if isinstance(value, datetime):
        dt_value = value
    else:
        text = str(value).strip()
        if not text:
            return None
        candidate = text.replace("Z", "+00:00")
        try:
            dt_value = datetime.fromisoformat(candidate)
        except ValueError:
            dt_value = None
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d",
            ):
                try:
                    dt_value = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt_value is None:
                return None

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value.astimezone(timezone.utc)


def pick_first(record: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_symbols(raw_value: Any, fallback_ticker: Optional[str] = None) -> List[str]:
    items: List[str] = []
    if isinstance(raw_value, list):
        items = [str(item).strip().upper() for item in raw_value if str(item).strip()]
    elif isinstance(raw_value, str):
        items = [part.strip().upper() for part in raw_value.split(",") if part.strip()]
    elif raw_value is not None:
        text = str(raw_value).strip().upper()
        if text:
            items = [text]

    if fallback_ticker:
        ticker = fallback_ticker.strip().upper()
        if ticker and ticker not in items:
            items.insert(0, ticker)

    unique_items: List[str] = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
    return unique_items


def build_dedupe_key(
    source_type: str,
    ticker: Optional[str],
    symbols: Iterable[str],
    published_at: str,
    title: str,
) -> str:
    key_material = "|".join(
        [
            source_type,
            ticker or "",
            ",".join(symbols),
            published_at,
            title.strip(),
        ]
    )
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()


def target_table_name(source_type: str) -> str:
    if source_type == "stock_news":
        return "stock_news_daily"
    return "general_news_daily"


def normalize_record(
    record: Dict[str, Any],
    source_type: str,
    fallback_ticker: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    title = pick_first(record, "title", "headline")
    published_raw = pick_first(
        record,
        "publishedDate",
        "published_date",
        "publishedAt",
        "date",
        "timestamp",
    )

    published_at = normalize_datetime(published_raw)
    if not title or not published_at:
        return None

    symbols = normalize_symbols(
        pick_first(record, "symbols", "symbol", "ticker", "tickers"),
        fallback_ticker=fallback_ticker,
    )
    primary_ticker = fallback_ticker or (symbols[0] if symbols else None)

    content = pick_first(record, "text", "content", "body", "snippet", "summary")
    publisher = pick_first(record, "publisher", "source", "site")
    site = pick_first(record, "site", "source")

    published_iso = published_at.isoformat()
    clean_title = str(title).strip()
    clean_content = str(content).strip() if content not in (None, "") else None
    clean_publisher = str(publisher).strip() if publisher not in (None, "") else None
    clean_site = str(site).strip() if site not in (None, "") else None

    normalized = {
        "ticker": primary_ticker,
        "symbols": symbols,
        "title": clean_title,
        "content": clean_content,
        "published_at": published_iso,
        "publisher": clean_publisher,
        "site": clean_site,
        "dedupe_key": build_dedupe_key(source_type, primary_ticker, symbols, published_iso, clean_title),
        "_source_type": source_type,
        "_target_table": target_table_name(source_type),
    }
    if source_type == "general_news":
        normalized.pop("ticker", None)
        normalized.pop("symbols", None)
    return normalized


def in_window(published_at: str, start_date: date, end_date: date) -> bool:
    published_dt = normalize_datetime(published_at)
    if published_dt is None:
        return False

    start_dt = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)
    return start_dt <= published_dt < end_dt


def fetch_endpoint(
    client: httpx.Client,
    endpoint: str,
    api_key: str,
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    query = dict(params)
    query["apikey"] = api_key
    response = client.get(f"{FMP_BASE_URL}{endpoint}", params=query)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected FMP response for {endpoint}: expected list, got {type(payload).__name__}")
    return payload


def fetch_symbol_news(
    http_client: httpx.Client,
    api_key: str,
    ticker: str,
    source_type: str,
) -> List[Dict[str, Any]]:
    endpoint = "/news/stock" if source_type == "stock_news" else "/news/press-releases"
    return fetch_endpoint(http_client, endpoint, api_key, {"symbols": ticker})


def fetch_general_news(
    http_client: httpx.Client,
    api_key: str,
    page_size: int,
    general_pages: int,
    start_date: date,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for page in range(general_pages):
        try:
            payload = fetch_endpoint(
                http_client,
                "/news/general-latest",
                api_key,
                {"page": page, "limit": page_size},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 400:
                print(f"Reached the last available general-news page at page={page}. Stopping pagination.")
                break
            raise
        if not payload:
            break

        rows.extend(payload)

        normalized_dates = [
            normalize_datetime(
                pick_first(item, "publishedDate", "published_date", "publishedAt", "date", "timestamp")
            )
            for item in payload
        ]
        normalized_dates = [item for item in normalized_dates if item is not None]
        if normalized_dates and all(item.date() < start_date for item in normalized_dates):
            break

    return rows


def chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def utc_day(value: str) -> date:
    normalized = normalize_datetime(value)
    if normalized is None:
        raise ValueError(f"Cannot extract date from {value}")
    return normalized.date()


def apply_daily_limits(
    rows: List[Dict[str, Any]],
    max_stock_news_per_day: int,
    max_general_news_per_day: int,
) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: row["published_at"], reverse=True)
    counters: Dict[tuple, int] = {}
    kept: List[Dict[str, Any]] = []

    for row in sorted_rows:
        source_type = row["_source_type"]
        day = utc_day(row["published_at"])
        if source_type == "stock_news":
            key = (source_type, row.get("ticker"), day)
            limit = max_stock_news_per_day
        else:
            key = (source_type, day)
            limit = max_general_news_per_day

        count = counters.get(key, 0)
        if count >= limit:
            continue

        counters[key] = count + 1
        kept.append(row)

    return sorted(kept, key=lambda row: (row["published_at"], row.get("ticker") or ""))


def strip_internal_fields(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for row in rows:
        cleaned.append({key: value for key, value in row.items() if not key.startswith("_")})
    return cleaned


def main():
    args = parse_args()
    selected_types = {item.strip() for item in args.news_types.split(",") if item.strip()}
    invalid_types = selected_types - {"stock_news", "general_news"}
    if invalid_types:
        raise SystemExit(f"Unsupported news types: {', '.join(sorted(invalid_types))}")

    start_date = parse_date_arg(args.start_date)
    end_date = parse_date_arg(args.end_date)
    if end_date < start_date:
        raise SystemExit("--end-date must be on or after --start-date")

    tickers = [item.strip().upper() for item in args.tickers.split(",") if item.strip()]
    if not tickers and selected_types != {"general_news"}:
        raise SystemExit("Provide at least one ticker unless you only ingest general_news")

    print("Loading environment variables...")
    load_dotenv()

    fmp_api_key = os.getenv("FMP_API_KEY")
    if not fmp_api_key:
        raise SystemExit("Set FMP_API_KEY in your environment or .env file")

    supabase: Optional[Client] = None
    if not args.dry_run:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)

    print(
        f"Fetching news from {args.start_date} to {args.end_date} for "
        f"{', '.join(tickers) if tickers else 'general_news only'}..."
    )

    collected_rows: List[Dict[str, Any]] = []

    with httpx.Client(timeout=30.0) as http_client:
        for ticker in tickers:
            if "stock_news" in selected_types:
                print(f"Downloading stock news for {ticker}...")
                payload = fetch_symbol_news(http_client, fmp_api_key, ticker, "stock_news")
                for record in payload:
                    normalized = normalize_record(record, "stock_news", fallback_ticker=ticker)
                    if normalized and in_window(normalized["published_at"], start_date, end_date):
                        collected_rows.append(normalized)
                time.sleep(args.sleep_seconds)

        if "general_news" in selected_types:
            print("Downloading general market news...")
            payload = fetch_general_news(
                http_client,
                fmp_api_key,
                page_size=args.page_size,
                general_pages=args.general_pages,
                start_date=start_date,
            )
            for record in payload:
                normalized = normalize_record(record, "general_news")
                if normalized and in_window(normalized["published_at"], start_date, end_date):
                    collected_rows.append(normalized)

    deduped_rows = list({row["dedupe_key"]: row for row in collected_rows}.values())
    final_rows = apply_daily_limits(
        deduped_rows,
        max_stock_news_per_day=args.max_stock_news_per_day,
        max_general_news_per_day=args.max_general_news_per_day,
    )

    grouped_rows: Dict[str, List[Dict[str, Any]]] = {
        "general_news_daily": [],
        "stock_news_daily": [],
    }
    for row in final_rows:
        grouped_rows[row["_target_table"]].append(row)

    print(
        "Prepared rows: "
        f"general_news_daily={len(grouped_rows['general_news_daily'])}, "
        f"stock_news_daily={len(grouped_rows['stock_news_daily'])}."
    )

    if args.dry_run:
        preview_count = 5
        for table_name, rows in grouped_rows.items():
            for row in rows[:preview_count]:
                label = row.get("ticker", "GENERAL")
                print(f"- {table_name} | {row['published_at']} | {label} | {row['title']}")
        print("Dry run only. No database writes performed.")
        return

    assert supabase is not None
    for table_name, rows in grouped_rows.items():
        cleaned_rows = strip_internal_fields(rows)
        for batch in chunked(cleaned_rows, 500):
            supabase.table(table_name).upsert(batch, on_conflict="dedupe_key").execute()

    print("News ingestion complete.")


if __name__ == "__main__":
    main()
