#!/usr/bin/env python3
import argparse
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
SUPPORTED_INDICATORS = [
    "sma",
    "ema",
    "wma",
    "dema",
    "tema",
    "rsi",
    "standarddeviation",
    "williams",
    "adx",
]
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2026-04-10"
DEFAULT_PERIOD_LENGTHS = [10]
NON_INDICATOR_FIELDS = {
    "date",
    "label",
    "symbol",
    "change",
    "changePercent",
    "vwap",
    "unadjustedVolume",
    "open",
    "high",
    "low",
    "close",
    "volume",
}
INDICATOR_VALUE_KEYS = {
    "sma": ["sma"],
    "ema": ["ema"],
    "wma": ["wma"],
    "dema": ["dema"],
    "tema": ["tema"],
    "rsi": ["rsi"],
    "standarddeviation": ["standardDeviation", "standarddeviation"],
    "williams": ["williams"],
    "adx": ["adx"],
}


class FmpAccessError(RuntimeError):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest FMP technical indicators into technical_indicators_daily")
    parser.add_argument("--tickers", default=",".join(DOW_30_TICKERS))
    parser.add_argument("--indicators", default=",".join(SUPPORTED_INDICATORS))
    parser.add_argument("--period-lengths", default=",".join(str(value) for value in DEFAULT_PERIOD_LENGTHS))
    parser.add_argument("--timeframe", default="1day", help="FMP timeframe, for example 1day")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Inclusive start date, format YYYY-MM-DD")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE, help="Inclusive end date, format YYYY-MM-DD")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--db-batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count rows without writing to Supabase")
    parser.add_argument("--api-key", default=os.getenv("FMP_API_KEY") or os.getenv("FINANCIAL_MODELING_PREP_API_KEY"))
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


def parse_numeric(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def round_metric(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 2)


def sanitize_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): sanitize_json(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item) for item in value]
    return str(value)


def build_url(indicator: str, symbol: str, period_length: int, timeframe: str, api_key: str) -> str:
    return (
        f"{FMP_BASE_URL}/technical-indicators/{indicator}"
        f"?symbol={symbol}&periodLength={period_length}&timeframe={timeframe}&apikey={api_key}"
    )


def fetch_endpoint(
    client: httpx.Client,
    indicator: str,
    ticker: str,
    period_length: int,
    timeframe: str,
    api_key: str,
) -> List[Dict[str, Any]]:
    url = build_url(indicator, ticker, period_length, timeframe, api_key)
    response = client.get(url)
    if response.status_code == 402:
        raise FmpAccessError(
            "FMP returned 402 Payment Required for the technical indicators endpoint."
        )
    if response.status_code == 403:
        raise FmpAccessError(
            "FMP returned 403 for the technical indicators endpoint. Check that your API key is valid."
        )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError(
            f"Unexpected FMP response for indicator={indicator}, ticker={ticker}: "
            f"expected list, got {type(payload).__name__}"
        )
    return payload


def extract_indicator_value(record: Dict[str, Any], indicator: str) -> Optional[float]:
    for key in INDICATOR_VALUE_KEYS[indicator]:
        number = parse_numeric(record.get(key))
        if number is not None:
            return round_metric(number)

    numeric_candidates: List[float] = []
    for key, value in record.items():
        if key in NON_INDICATOR_FIELDS:
            continue
        number = parse_numeric(value)
        if number is not None:
            numeric_candidates.append(number)

    if len(numeric_candidates) == 1:
        return round_metric(numeric_candidates[0])
    return None


def merge_rows(
    rows_by_key: Dict[Tuple[str, str, int, str], Dict[str, Any]],
    ticker: str,
    indicator: str,
    period_length: int,
    timeframe: str,
    payload: Iterable[Dict[str, Any]],
    start_date: date,
    end_date: date,
):
    for record in payload:
        event_dt = normalize_datetime(record.get("date"))
        if event_dt is None:
            continue
        event_date = event_dt.date()
        if event_date < start_date or event_date > end_date:
            continue

        indicator_value = extract_indicator_value(record, indicator)
        if indicator_value is None:
            continue

        key = (ticker, timeframe, period_length, event_date.isoformat())
        row = rows_by_key.setdefault(
            key,
            {
                "provider": "fmp",
                "ticker": ticker,
                "timeframe": timeframe,
                "period_length": period_length,
                "event_date": event_date.isoformat(),
                "sma": None,
                "ema": None,
                "wma": None,
                "dema": None,
                "tema": None,
                "rsi": None,
                "standarddeviation": None,
                "williams": None,
                "adx": None,
                "raw_payload": {},
            },
        )
        row[indicator] = indicator_value
        row["raw_payload"][indicator] = sanitize_json(record)


def flush_batch(supabase: Client, rows: List[Dict[str, Any]]):
    if not rows:
        return
    supabase.table("technical_indicators_daily").upsert(
        rows,
        on_conflict="provider,ticker,timeframe,period_length,event_date",
    ).execute()


def main():
    load_dotenv()
    args = parse_args()

    if not args.api_key:
        raise SystemExit("Set FMP_API_KEY or FINANCIAL_MODELING_PREP_API_KEY, or pass --api-key")

    supabase: Optional[Client] = None
    if not args.dry_run:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)

    start_date = parse_date_arg(args.start_date)
    end_date = parse_date_arg(args.end_date)
    if end_date < start_date:
        raise SystemExit("--end-date must be on or after --start-date")

    indicators = [value.strip().lower() for value in args.indicators.split(",") if value.strip()]
    unsupported = [value for value in indicators if value not in SUPPORTED_INDICATORS]
    if unsupported:
        raise SystemExit(f"Unsupported indicators: {', '.join(unsupported)}")

    try:
        period_lengths = [int(value.strip()) for value in args.period_lengths.split(",") if value.strip()]
    except ValueError as exc:
        raise SystemExit("--period-lengths must be comma-separated integers") from exc
    if any(value <= 0 for value in period_lengths):
        raise SystemExit("--period-lengths must contain positive integers")

    tickers = [value.strip().upper() for value in args.tickers.split(",") if value.strip()]
    print("🚀 Starting FMP technical indicator ingestion...")
    print(
        f" Tracking {len(tickers)} tickers across indicators {','.join(indicators)}, "
        f"period lengths {','.join(str(value) for value in period_lengths)}, "
        f"timeframe {args.timeframe}, window {start_date.isoformat()} to {end_date.isoformat()}..."
    )

    total_rows = 0
    pending_rows: List[Dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout_seconds, follow_redirects=True) as client:
        for ticker in tickers:
            print(f" Downloading technical indicators for {ticker}...")
            try:
                rows_by_key: Dict[Tuple[str, str, int, str], Dict[str, Any]] = {}
                for period_length in period_lengths:
                    for indicator in indicators:
                        payload = fetch_endpoint(
                            client=client,
                            indicator=indicator,
                            ticker=ticker,
                            period_length=period_length,
                            timeframe=args.timeframe,
                            api_key=args.api_key,
                        )
                        merge_rows(
                            rows_by_key=rows_by_key,
                            ticker=ticker,
                            indicator=indicator,
                            period_length=period_length,
                            timeframe=args.timeframe,
                            payload=payload,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        time.sleep(args.sleep_seconds)
            except FmpAccessError as exc:
                raise SystemExit(str(exc)) from exc
            except Exception as exc:
                print(f"   ❌ Failed to process {ticker}: {exc}")
                continue

            ticker_rows = list(rows_by_key.values())
            if not ticker_rows:
                print(f"   ⚠️ No technical indicator rows found for {ticker}")
                continue

            for row in ticker_rows:
                row["raw_payload"] = sanitize_json(row["raw_payload"])

            pending_rows.extend(ticker_rows)
            total_rows += len(ticker_rows)
            print(f"   ✅ Prepared {len(ticker_rows)} daily rows for {ticker}")

            if args.dry_run:
                continue

            if len(pending_rows) >= args.db_batch_size:
                flush_batch(supabase, pending_rows)
                print(f"   ↳ Upserted {len(pending_rows)} rows")
                pending_rows = []

    if args.dry_run:
        print(f"🏁 FMP technical indicator dry run complete. Prepared {total_rows} rows.")
        return

    flush_batch(supabase, pending_rows)
    if pending_rows:
        print(f"   ↳ Upserted {len(pending_rows)} rows")

    print(f"🏁 FMP technical indicator ingestion complete. Prepared {total_rows} rows.")


if __name__ == "__main__":
    main()
