#!/usr/bin/env python3
import hashlib
import json
import os
import random
import socket
import ssl
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from supabase import Client, create_client
import certifi

FMP_BASE_URL = "https://financialmodelingprep.com/stable"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def default_start_date() -> str:
    return (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()


def default_end_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


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


def build_dedupe_key(source_type: str, ticker: Optional[str], symbols: Iterable[str], published_at: str, title: str) -> str:
    key_material = "|".join([source_type, ticker or "", ",".join(symbols), published_at, title.strip()])
    return hashlib.sha256(key_material.encode("utf-8")).hexdigest()


def in_window(published_at: str, start_date: date, end_date: date) -> bool:
    published_dt = normalize_datetime(published_at)
    if published_dt is None:
        return False
    start_dt = datetime.combine(start_date, dt_time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)
    return start_dt <= published_dt < end_dt


def build_news_url(endpoint: str, request_date: date, page: int, limit: int, ticker: Optional[str] = None) -> str:
    params = {
        "from": request_date.isoformat(),
        "to": request_date.isoformat(),
        "page": page,
        "limit": limit,
    }
    if ticker:
        params["symbols"] = ticker
    return f"{FMP_BASE_URL}/{endpoint}?{urlencode(params)}"


def fetch_json(
    url: str,
    api_key: str,
    sleep_seconds: float,
    timeout_seconds: float,
    max_retries: int,
    retry_backoff_seconds: float,
) -> List[Dict[str, Any]]:
    req = Request(url, headers={"apikey": api_key})
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(req, timeout=timeout_seconds, context=ssl_context) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            time.sleep(sleep_seconds)
            if not isinstance(payload, list):
                raise ValueError(f"Unexpected FMP response for {url}: expected list, got {type(payload).__name__}")
            return payload
        except HTTPError as e:
            last_error = e
            if e.code in {400, 402, 403, 404}:
                raise
            if e.code not in RETRYABLE_STATUS_CODES or attempt == max_retries:
                raise
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(f"⚠️ HTTP {e.code} fetching {url} (attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
        except (URLError, TimeoutError, socket.timeout, json.JSONDecodeError) as e:
            last_error = e
            if attempt == max_retries:
                raise
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(f"⚠️ Network/error fetching {url}: {e} (attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def fetch_fmp_news_by_day(
    endpoint: str,
    api_key: str,
    start_date: date,
    end_date: date,
    page_size: int,
    max_pages: int,
    sleep_seconds: float,
    timeout_seconds: float,
    max_retries: int,
    retry_backoff_seconds: float,
    ticker: Optional[str] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    total_days = (end_date - start_date).days + 1
    processed_days = 0
    current_day = start_date
    while current_day <= end_date:
        processed_days += 1
        print(
            f"Processing {endpoint}"
            f"{f' for {ticker}' if ticker else ''}: "
            f"{current_day.isoformat()} ({processed_days}/{total_days})"
        )
        for page in range(max_pages):
            url = build_news_url(endpoint, current_day, page, page_size, ticker=ticker)
            try:
                payload = fetch_json(
                    url=url,
                    api_key=api_key,
                    sleep_seconds=sleep_seconds,
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                    retry_backoff_seconds=retry_backoff_seconds,
                )
            except HTTPError as exc:
                if exc.code in {400, 402, 403, 404}:
                    print(
                        f"FMP stopped {endpoint}"
                        f"{f' for {ticker}' if ticker else ''} on {current_day.isoformat()} "
                        f"at page={page} with HTTP {exc.code}."
                    )
                    break
                raise

            if not payload:
                break

            rows.extend(payload)
            print(
                f"  page {page}: fetched {len(payload)} rows "
                f"(running total {len(rows)})"
            )
            if len(payload) < page_size:
                break
        current_day += timedelta(days=1)
    return rows


def normalize_general_news_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = pick_first(record, "title", "headline")
    published_at = normalize_datetime(pick_first(record, "publishedDate", "published_date", "publishedAt", "date", "timestamp"))
    if not title or not published_at:
        return None
    content = pick_first(record, "text", "content", "body", "snippet", "summary")
    publisher = pick_first(record, "publisher", "source", "site")
    site = pick_first(record, "site", "source")
    published_iso = published_at.isoformat()
    clean_title = str(title).strip()
    return {
        "title": clean_title,
        "content": str(content).strip() if content not in (None, "") else None,
        "published_at": published_iso,
        "publisher": str(publisher).strip() if publisher not in (None, "") else None,
        "site": str(site).strip() if site not in (None, "") else None,
        "dedupe_key": build_dedupe_key("general_news", None, [], published_iso, clean_title),
        "_source_type": "general_news",
        "_target_table": "general_news_daily",
    }


def normalize_stock_news_record(record: Dict[str, Any], fallback_ticker: str) -> Optional[Dict[str, Any]]:
    title = pick_first(record, "title", "headline")
    published_at = normalize_datetime(pick_first(record, "publishedDate", "published_date", "publishedAt", "date", "timestamp"))
    if not title or not published_at:
        return None
    symbols = normalize_symbols(pick_first(record, "symbols", "symbol", "ticker", "tickers"), fallback_ticker=fallback_ticker)
    primary_ticker = fallback_ticker or (symbols[0] if symbols else None)
    content = pick_first(record, "text", "content", "body", "snippet", "summary")
    publisher = pick_first(record, "publisher", "source", "site")
    site = pick_first(record, "site", "source")
    published_iso = published_at.isoformat()
    clean_title = str(title).strip()
    return {
        "ticker": primary_ticker,
        "symbols": symbols,
        "title": clean_title,
        "content": str(content).strip() if content not in (None, "") else None,
        "published_at": published_iso,
        "publisher": str(publisher).strip() if publisher not in (None, "") else None,
        "site": str(site).strip() if site not in (None, "") else None,
        "dedupe_key": build_dedupe_key("stock_news", primary_ticker, symbols, published_iso, clean_title),
        "_source_type": "stock_news",
        "_target_table": "stock_news_daily",
    }


def apply_daily_limit(rows: List[Dict[str, Any]], per_day_limit: int, key_field: Optional[str] = None) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=lambda row: row["published_at"], reverse=True)
    counters: Dict[tuple, int] = {}
    kept: List[Dict[str, Any]] = []
    for row in sorted_rows:
        day = normalize_datetime(row["published_at"]).date()
        counter_key = (day, row.get(key_field)) if key_field else (day,)
        count = counters.get(counter_key, 0)
        if count >= per_day_limit:
            continue
        counters[counter_key] = count + 1
        kept.append(row)
    return sorted(kept, key=lambda row: (row["published_at"], row.get(key_field) or ""))


def strip_internal_fields(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{key: value for key, value in row.items() if not key.startswith("_")} for row in rows]


def print_source_span(rows: List[Dict[str, Any]], source_type: str) -> None:
    if not rows:
        print(f"No rows fetched from source {source_type}.")
        return
    ordered = sorted(rows, key=lambda row: row["published_at"])
    print(
        f"Available {source_type} span from API: "
        f"{ordered[0]['published_at']} to {ordered[-1]['published_at']} "
        f"({len(rows)} rows fetched before date filtering/limits)."
    )


def load_env_and_clients(require_supabase: bool) -> tuple[str, Optional[Client]]:
    load_dotenv()
    api_key = os.getenv("FMP_API_KEY") or os.getenv("FINANCIAL_MODELING_PREP_API_KEY")
    if not api_key:
        raise SystemExit("Set FMP_API_KEY or FINANCIAL_MODELING_PREP_API_KEY")

    if not require_supabase:
        return api_key, None

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    return api_key, create_client(supabase_url, supabase_key)
