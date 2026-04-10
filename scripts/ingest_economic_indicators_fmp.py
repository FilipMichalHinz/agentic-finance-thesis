#!/usr/bin/env python3
import argparse
import os
import time
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
DEFAULT_INDICATORS = ["GDP", "CPI", "inflationRate", "unemploymentRate"]
DEFAULT_START_DATE = "2024-01-01"
DEFAULT_END_DATE = "2026-04-10"
INDICATOR_ALIASES = {
    "gdp": "GDP",
    "cpi": "CPI",
    "inflation": "inflationRate",
    "inflationrate": "inflationRate",
    "unemployment": "unemploymentRate",
    "unemploymentrate": "unemploymentRate",
}
NON_VALUE_KEYS = {
    "date",
    "name",
    "country",
    "symbol",
    "label",
    "period",
    "calendarYear",
    "updatedAt",
}


class FmpAccessError(RuntimeError):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest FMP economic indicators into economic_indicators")
    parser.add_argument("--indicators", default=",".join(DEFAULT_INDICATORS))
    parser.add_argument("--country", default="US")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE, help="Inclusive start date, format YYYY-MM-DD")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE, help="Inclusive end date, format YYYY-MM-DD")
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--db-batch-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count rows without writing to Supabase")
    parser.add_argument("--api-key", default=os.getenv("FMP_API_KEY") or os.getenv("FINANCIAL_MODELING_PREP_API_KEY"))
    return parser.parse_args()


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


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


def build_url(name: str, country: str, api_key: str, start_date: date, end_date: date) -> str:
    return (
        f"{FMP_BASE_URL}/economic-indicators"
        f"?name={name}"
        f"&country={country}"
        f"&from={start_date.isoformat()}"
        f"&to={end_date.isoformat()}"
        f"&apikey={api_key}"
    )


def normalize_indicator_name(value: str) -> Tuple[str, str]:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Indicator names cannot be empty")
    canonical = INDICATOR_ALIASES.get(stripped.lower(), stripped)
    return stripped, canonical


def fetch_indicator_payload(
    client: httpx.Client,
    name: str,
    country: str,
    api_key: str,
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    response = client.get(build_url(name, country, api_key, start_date, end_date))
    if response.status_code == 402:
        raise FmpAccessError(
            "FMP returned 402 Payment Required for the economic indicators endpoint."
        )
    if response.status_code == 403:
        raise FmpAccessError(
            "FMP returned 403 for the economic indicators endpoint. Check that your API key is valid."
        )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        return [payload]
    if not isinstance(payload, list):
        raise ValueError(
            f"Unexpected FMP response for economic indicator {name}: "
            f"expected list, got {type(payload).__name__}"
        )
    return payload


def extract_value(record: Dict[str, Any], indicator_name: str) -> Optional[float]:
    preferred_keys = [
        "value",
        indicator_name,
        indicator_name.lower(),
        indicator_name.upper(),
    ]
    for key in preferred_keys:
        number = parse_numeric(record.get(key))
        if number is not None:
            return round_metric(number)

    numeric_candidates: List[float] = []
    for key, value in record.items():
        if key in NON_VALUE_KEYS:
            continue
        number = parse_numeric(value)
        if number is not None:
            numeric_candidates.append(number)

    if len(numeric_candidates) == 1:
        return round_metric(numeric_candidates[0])
    return None


def build_rows(
    indicator_name: str,
    country: str,
    payload: Iterable[Dict[str, Any]],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for record in payload:
        raw_date = record.get("date")
        if not raw_date:
            continue
        try:
            event_date = parse_date_arg(str(raw_date)[:10])
        except ValueError:
            continue
        if event_date < start_date or event_date > end_date:
            continue

        value = extract_value(record, indicator_name)
        if value is None:
            continue

        rows.append({
            "provider": "fmp",
            "country": country,
            "indicator_name": indicator_name,
            "event_date": event_date.isoformat(),
            "value": value,
            "raw_payload": sanitize_json(record),
        })
    return rows


def flush_batch(supabase: Client, rows: List[Dict[str, Any]]):
    if not rows:
        return
    supabase.table("economic_indicators").upsert(
        rows,
        on_conflict="provider,country,indicator_name,event_date",
    ).execute()


def main():
    load_dotenv()
    args = parse_args()

    if not args.api_key:
        raise SystemExit("Set FMP_API_KEY or FINANCIAL_MODELING_PREP_API_KEY, or pass --api-key")

    start_date = parse_date_arg(args.start_date)
    end_date = parse_date_arg(args.end_date)
    if end_date < start_date:
        raise SystemExit("--end-date must be on or after --start-date")

    indicators = [normalize_indicator_name(value) for value in args.indicators.split(",") if value.strip()]

    supabase: Optional[Client] = None
    if not args.dry_run:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        supabase = create_client(supabase_url, supabase_key)

    print("🚀 Starting FMP economic indicator ingestion...")
    print(
        f" Tracking indicators {','.join(canonical for _, canonical in indicators)} for {args.country} "
        f"from {start_date.isoformat()} to {end_date.isoformat()}..."
    )

    total_rows = 0
    pending_rows: List[Dict[str, Any]] = []
    with httpx.Client(timeout=args.timeout_seconds, follow_redirects=True) as client:
        for requested_name, canonical_name in indicators:
            print(f" Downloading economic indicator {canonical_name}...")
            try:
                payload = fetch_indicator_payload(
                    client,
                    canonical_name,
                    args.country,
                    args.api_key,
                    start_date,
                    end_date,
                )
            except FmpAccessError as exc:
                raise SystemExit(str(exc)) from exc
            except Exception as exc:
                print(f"   ❌ Failed to process {canonical_name}: {exc}")
                continue

            rows = build_rows(canonical_name, args.country, payload, start_date, end_date)
            if not rows:
                print(f"   ⚠️ No rows found for {canonical_name}")
                continue

            pending_rows.extend(rows)
            total_rows += len(rows)
            if requested_name.lower() != canonical_name.lower():
                print(f"   ✅ Prepared {len(rows)} rows for {requested_name} (stored as {canonical_name})")
            else:
                print(f"   ✅ Prepared {len(rows)} rows for {canonical_name}")

            if args.dry_run:
                time.sleep(args.sleep_seconds)
                continue

            if len(pending_rows) >= args.db_batch_size:
                flush_batch(supabase, pending_rows)
                print(f"   ↳ Upserted {len(pending_rows)} rows")
                pending_rows = []

            time.sleep(args.sleep_seconds)

    if args.dry_run:
        print(f"🏁 FMP economic indicator dry run complete. Prepared {total_rows} rows.")
        return

    flush_batch(supabase, pending_rows)
    if pending_rows:
        print(f"   ↳ Upserted {len(pending_rows)} rows")

    print(f"🏁 FMP economic indicator ingestion complete. Prepared {total_rows} rows.")


if __name__ == "__main__":
    main()
