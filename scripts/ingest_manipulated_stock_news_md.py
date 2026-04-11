#!/usr/bin/env python3
import argparse
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from supabase import Client, create_client

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS


DEFAULT_START_DATE = "2025-04-11"
DEFAULT_END_DATE = "2026-04-08"
REQUIRED_FIELDS = ("ticker", "title", "content", "publisher", "site", "falsity")
FIELD_MAP = {
    "ticker": "ticker",
    "title": "title",
    "content": "content",
    "publisher": "publisher",
    "site": "site",
    "falsity": "falsity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest manipulated stock news from a markdown file into manipulated_stock_news_daily."
    )
    parser.add_argument("--input-file", required=True, help="Path to the markdown file containing fake news rows.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Inclusive start date, format YYYY-MM-DD.")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE, help="Inclusive end date, format YYYY-MM-DD.")
    parser.add_argument("--dry-run", action="store_true", help="Parse, schedule, and validate rows without writing.")
    return parser.parse_args()


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


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


def chunked(values: Sequence[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY are required.")
    return create_client(supabase_url, supabase_key)


def finalize_record(current: Dict[str, str], record_number: int) -> Dict[str, str]:
    missing = [field for field in REQUIRED_FIELDS if not current.get(field)]
    if missing:
        raise ValueError(f"Record {record_number} is missing required fields: {', '.join(missing)}")
    return {field: current[field].strip() for field in REQUIRED_FIELDS}


def parse_markdown_rows(input_path: Path) -> List[Dict[str, str]]:
    text = input_path.read_text(encoding="utf-8")
    rows: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        cleaned = stripped.replace("**", "").strip()
        if ":" not in cleaned:
            continue

        label, value = cleaned.split(":", 1)
        field_name = FIELD_MAP.get(label.strip().lower())
        if field_name is None:
            continue

        if field_name == "ticker" and current:
            rows.append(finalize_record(current, len(rows) + 1))
            current = {}

        current[field_name] = value.strip()

    if current:
        rows.append(finalize_record(current, len(rows) + 1))

    return rows


def classify_falsity(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("decontextualized"):
        return "mild"
    if normalized.startswith("very false"):
        return "high"
    raise ValueError(f"Unsupported falsity label: {value}")


def validate_parsed_rows(rows: List[Dict[str, str]]) -> None:
    if len(rows) != 60:
        raise ValueError(f"Expected 60 parsed rows, found {len(rows)}")

    ticker_counts = Counter(row["ticker"] for row in rows)
    expected_tickers = set(DOW_30_TICKERS)
    actual_tickers = set(ticker_counts)
    missing = sorted(expected_tickers - actual_tickers)
    extra = sorted(actual_tickers - expected_tickers)
    if missing or extra:
        problems: List[str] = []
        if missing:
            problems.append(f"missing tickers: {', '.join(missing)}")
        if extra:
            problems.append(f"unexpected tickers: {', '.join(extra)}")
        raise ValueError("Parsed markdown ticker set mismatch: " + "; ".join(problems))

    bad_counts = {ticker: count for ticker, count in ticker_counts.items() if count != 2}
    if bad_counts:
        details = ", ".join(f"{ticker}={count}" for ticker, count in sorted(bad_counts.items()))
        raise ValueError(f"Each ticker must appear exactly twice. Found: {details}")

    severity_counts = Counter(classify_falsity(row["falsity"]) for row in rows)
    if severity_counts.get("mild", 0) != 30 or severity_counts.get("high", 0) != 30:
        raise ValueError(
            "Expected 30 mild and 30 high rows based on falsity labels. "
            f"Found: {dict(sorted(severity_counts.items()))}"
        )

    per_ticker_severity: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        per_ticker_severity[row["ticker"]][classify_falsity(row["falsity"])] += 1

    invalid_tickers = []
    for ticker, counts in sorted(per_ticker_severity.items()):
        if counts.get("mild", 0) != 1 or counts.get("high", 0) != 1:
            invalid_tickers.append(f"{ticker}={dict(sorted(counts.items()))}")
    if invalid_tickers:
        raise ValueError(
            "Each ticker must have one mild and one high row. Found: " + ", ".join(invalid_tickers)
        )


def fetch_market_trading_dates(
    supabase: Client,
    start_date: date,
    end_date: date,
    tickers: Sequence[str],
    page_size: int = 1000,
) -> List[date]:
    start_iso = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc).isoformat()
    end_iso = datetime.combine(end_date, dt_time.max, tzinfo=timezone.utc).isoformat()
    trading_dates: set[date] = set()

    for ticker_chunk in chunked(list(tickers), 20):
        offset = 0
        while True:
            response = (
                supabase.table("market_prices_daily")
                .select("ticker,event_timestamp")
                .in_("ticker", ticker_chunk)
                .gte("event_timestamp", start_iso)
                .lte("event_timestamp", end_iso)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            batch = response.data or []
            for row in batch:
                event_dt = parse_iso_datetime(row.get("event_timestamp"))
                if event_dt is not None:
                    trading_dates.add(event_dt.date())
            if len(batch) < page_size:
                break
            offset += page_size

    if not trading_dates:
        raise ValueError(
            "No trading dates found in market_prices_daily for the requested range. "
            "Ingest market prices before loading manipulated news."
        )

    return sorted(trading_dates)


def week_start_for(trading_date: date) -> date:
    return trading_date - timedelta(days=trading_date.weekday())


def group_trading_dates_by_week(trading_dates: Sequence[date]) -> List[Tuple[date, List[date]]]:
    grouped: Dict[date, List[date]] = defaultdict(list)
    for trading_date in trading_dates:
        grouped[week_start_for(trading_date)].append(trading_date)
    return [(week_start, sorted(grouped[week_start])) for week_start in sorted(grouped)]


def select_evenly_spaced_weeks(
    weekly_dates: Sequence[Tuple[date, List[date]]],
    count: int,
) -> List[Tuple[date, List[date]]]:
    if len(weekly_dates) < count:
        raise ValueError(
            f"Need at least {count} trading weeks with 2+ trading days, found {len(weekly_dates)}."
        )
    indices = [int(index * len(weekly_dates) / count) for index in range(count)]
    selected = [weekly_dates[index] for index in indices]
    if len({week_start for week_start, _ in selected}) != count:
        raise ValueError("Week selection produced duplicates; cannot build deterministic schedule.")
    return selected


def published_at_for(trading_date: date) -> str:
    return datetime.combine(trading_date, dt_time(23, 59, 59), tzinfo=timezone.utc).isoformat()


def build_scheduled_rows(rows: List[Dict[str, str]], trading_dates: Sequence[date]) -> List[Dict[str, Any]]:
    mild_rows = [row for row in rows if classify_falsity(row["falsity"]) == "mild"]
    high_rows = [row for row in rows if classify_falsity(row["falsity"]) == "high"]

    weekly_dates = group_trading_dates_by_week(trading_dates)
    eligible_weeks = [(week_start, dates) for week_start, dates in weekly_dates if len(dates) >= 2]
    selected_weeks = select_evenly_spaced_weeks(eligible_weeks, len(mild_rows))

    scheduled_rows: List[Dict[str, Any]] = []
    for row, (week_start, dates_in_week) in zip(mild_rows, selected_weeks):
        scheduled_rows.append(
            {
                **row,
                "published_at": published_at_for(dates_in_week[0]),
                "_week_start": week_start.isoformat(),
                "_severity": "mild",
            }
        )

    # Reverse the high-impact assignment so each ticker's mild/high rows land in different weeks.
    for row, (week_start, dates_in_week) in zip(high_rows, reversed(selected_weeks)):
        scheduled_rows.append(
            {
                **row,
                "published_at": published_at_for(dates_in_week[-1]),
                "_week_start": week_start.isoformat(),
                "_severity": "high",
            }
        )

    return scheduled_rows


def validate_scheduled_rows(rows: List[Dict[str, Any]], trading_dates: Sequence[date]) -> None:
    if len(rows) != 60:
        raise ValueError(f"Expected 60 scheduled rows, found {len(rows)}")

    trading_date_set = set(trading_dates)
    ticker_counts = Counter(row["ticker"] for row in rows)
    if any(count != 2 for count in ticker_counts.values()):
        raise ValueError("Each ticker must still have exactly 2 scheduled rows.")

    week_counts = Counter(row["_week_start"] for row in rows)
    overflowing_weeks = {week: count for week, count in week_counts.items() if count > 2}
    if overflowing_weeks:
        details = ", ".join(f"{week}={count}" for week, count in sorted(overflowing_weeks.items()))
        raise ValueError(f"Found trading weeks with more than 2 fake items: {details}")

    per_ticker_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        published_dt = parse_iso_datetime(row["published_at"])
        if published_dt is None or published_dt.date() not in trading_date_set:
            raise ValueError(f"Scheduled row has non-trading published_at: {row['ticker']} | {row['published_at']}")
        per_ticker_rows[row["ticker"]].append(row)

    for ticker, ticker_rows in sorted(per_ticker_rows.items()):
        severities = {row["_severity"] for row in ticker_rows}
        if severities != {"mild", "high"}:
            raise ValueError(f"{ticker} does not have one mild and one high row after scheduling.")
        week_starts = {row["_week_start"] for row in ticker_rows}
        if len(week_starts) != 2:
            raise ValueError(f"{ticker} has mild/high rows in the same trading week, which is not allowed.")

    duplicate_keys = Counter((row["ticker"], row["published_at"], row["title"]) for row in rows)
    duplicates = [key for key, count in duplicate_keys.items() if count > 1]
    if duplicates:
        raise ValueError(f"Found duplicate composite keys in scheduled rows: {duplicates}")


def print_dry_run_summary(rows: List[Dict[str, Any]]) -> None:
    ticker_counts = Counter(row["ticker"] for row in rows)
    severity_counts = Counter(row["_severity"] for row in rows)
    week_buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        week_buckets[row["_week_start"]].append(row)

    print(f"Prepared rows: manipulated_stock_news_daily={len(rows)}.")
    print(f"Unique tickers: {len(ticker_counts)}")
    print("Counts per falsity type:")
    for severity in ("mild", "high"):
        print(f"- {severity}: {severity_counts.get(severity, 0)}")

    print("Counts per ticker:")
    for ticker in sorted(ticker_counts):
        print(f"- {ticker}: {ticker_counts[ticker]}")

    print("Assigned trading dates by week:")
    for week_start in sorted(week_buckets):
        bucket = sorted(week_buckets[week_start], key=lambda row: row["published_at"])
        dates = ", ".join(row["published_at"][:10] for row in bucket)
        tickers = ", ".join(row["ticker"] for row in bucket)
        print(f"- {week_start}: count={len(bucket)} | dates={dates} | tickers={tickers}")


def strip_internal_fields(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in rows
    ]


def fetch_all_inserted_rows(supabase: Client, page_size: int = 1000) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        response = (
            supabase.table("manipulated_stock_news_daily")
            .select("ticker,title,falsity,published_at")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows


def validate_inserted_rows(rows: List[Dict[str, Any]]) -> None:
    if len(rows) != 60:
        raise ValueError(f"Expected 60 rows in manipulated_stock_news_daily after upsert, found {len(rows)}")

    ticker_counts = Counter(row["ticker"] for row in rows)
    bad_counts = {ticker: count for ticker, count in ticker_counts.items() if count != 2}
    if bad_counts:
        details = ", ".join(f"{ticker}={count}" for ticker, count in sorted(bad_counts.items()))
        raise ValueError(f"Inserted rows do not preserve 2 rows per ticker: {details}")

    week_counts: Counter[str] = Counter()
    for row in rows:
        published_dt = parse_iso_datetime(row.get("published_at"))
        if published_dt is None:
            raise ValueError(f"Inserted row has invalid published_at: {row}")
        week_counts[week_start_for(published_dt.date()).isoformat()] += 1

    overflowing_weeks = {week: count for week, count in week_counts.items() if count > 2}
    if overflowing_weeks:
        details = ", ".join(f"{week}={count}" for week, count in sorted(overflowing_weeks.items()))
        raise ValueError(f"Inserted rows exceed 2 fake items in a trading week: {details}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    start_date = parse_date_arg(args.start_date)
    end_date = parse_date_arg(args.end_date)
    if end_date < start_date:
        raise SystemExit("--end-date must be on or after --start-date")

    load_dotenv()
    supabase = get_supabase_client()

    parsed_rows = parse_markdown_rows(input_path)
    validate_parsed_rows(parsed_rows)

    trading_dates = fetch_market_trading_dates(
        supabase=supabase,
        start_date=start_date,
        end_date=end_date,
        tickers=DOW_30_TICKERS,
    )
    scheduled_rows = build_scheduled_rows(parsed_rows, trading_dates)
    validate_scheduled_rows(scheduled_rows, trading_dates)
    printable_rows = strip_internal_fields(scheduled_rows)

    if args.dry_run:
        print_dry_run_summary(scheduled_rows)
        print("Dry run only. No database writes performed.")
        return

    supabase.table("manipulated_stock_news_daily").upsert(
        printable_rows,
        on_conflict="ticker,published_at,title",
    ).execute()

    inserted_rows = fetch_all_inserted_rows(supabase)
    validate_inserted_rows(inserted_rows)
    print(f"Inserted {len(printable_rows)} rows into manipulated_stock_news_daily.")


if __name__ == "__main__":
    main()
