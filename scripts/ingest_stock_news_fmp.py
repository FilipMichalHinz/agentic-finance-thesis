#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    try:
        from src.ticker_universes import DOW_30_TICKERS
    except ModuleNotFoundError:
        DOW_30_TICKERS = []

from fmp_news_common import (
    apply_daily_limit,
    default_end_date,
    default_start_date,
    fetch_fmp_news_by_day,
    load_env_and_clients,
    normalize_stock_news_record,
    parse_date_arg,
    print_source_span,
    strip_internal_fields,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest FMP stock news into stock_news_daily")
    parser.add_argument("--tickers", default=",".join(DOW_30_TICKERS) if DOW_30_TICKERS else "NVDA")
    parser.add_argument("--start-date", default=default_start_date(), help="Inclusive start date, format YYYY-MM-DD")
    parser.add_argument("--end-date", default=default_end_date(), help="Inclusive end date, format YYYY-MM-DD")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-stock-news-per-day", type=int, default=10)
    parser.add_argument("--sleep-seconds", type=float, default=0.25)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    start_date = parse_date_arg(args.start_date)
    end_date = parse_date_arg(args.end_date)
    if end_date < start_date:
        raise SystemExit("--end-date must be on or after --start-date")

    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    print("Loading environment variables...")
    api_key, supabase = load_env_and_clients(require_supabase=not args.dry_run)

    print(f"Fetching FMP stock news from {args.start_date} to {args.end_date} for {', '.join(tickers)}...")
    rows = []
    for ticker in tickers:
        print(f"Downloading stock news for {ticker}...")
        payload = fetch_fmp_news_by_day(
            endpoint="news/stock",
            api_key=api_key,
            start_date=start_date,
            end_date=end_date,
            page_size=args.page_size,
            max_pages=args.max_pages,
            sleep_seconds=args.sleep_seconds,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            retry_backoff_seconds=args.retry_backoff_seconds,
            ticker=ticker,
        )
        ticker_rows = []
        for record in payload:
            normalized = normalize_stock_news_record(record, fallback_ticker=ticker)
            if normalized:
                ticker_rows.append(normalized)
        print_source_span(ticker_rows, f"stock_news:{ticker}")
        rows.extend(ticker_rows)

    deduped_rows = list({row["dedupe_key"]: row for row in rows}.values())
    final_rows = apply_daily_limit(deduped_rows, per_day_limit=args.max_stock_news_per_day, key_field="ticker")

    print(f"Prepared rows: stock_news_daily={len(final_rows)}.")

    if args.dry_run:
        for row in final_rows[:5]:
            print(f"- stock_news_daily | {row['published_at']} | {row['ticker']} | {row['title']}")
        print("Dry run only. No database writes performed.")
        return

    assert supabase is not None
    supabase.table("stock_news_daily").upsert(strip_internal_fields(final_rows), on_conflict="dedupe_key").execute()
    print("Stock news ingestion complete.")


if __name__ == "__main__":
    main()
