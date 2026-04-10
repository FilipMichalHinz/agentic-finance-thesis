#!/usr/bin/env python3
import argparse
import gzip
import json
import os
import random
import re
import socket
import sys
import time
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

try:
    from src.ticker_universes import DOW_30_TICKERS
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.ticker_universes import DOW_30_TICKERS

SEC_BASE = "https://www.sec.gov"
SEC_TIMEZONE = ZoneInfo("America/New_York")

DEFAULT_TICKERS = DOW_30_TICKERS
DEFAULT_FORMS = ["10-K", "10-Q", "8-K"]
DEFAULT_START_DATE = "2025-01-01"
DEFAULT_END_DATE = "2026-04-10"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def maybe_gzip_decode(data):
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    return data


def append_jsonl(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def fetch_url(
    url,
    dest_path,
    user_agent,
    sleep_seconds=0.2,
    timeout_seconds=30,
    max_retries=5,
    retry_backoff_seconds=2.0,
):
    # Fetch and cache remote resources with a minimal SEC-friendly delay.
    if dest_path and os.path.exists(dest_path):
        with open(dest_path, "rb") as f:
            return maybe_gzip_decode(f.read())
    req = Request(url, headers={"User-Agent": user_agent})
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(req, timeout=timeout_seconds) as resp:
                data = resp.read()
            if dest_path:
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    f.write(data)
            time.sleep(sleep_seconds)
            return maybe_gzip_decode(data)
        except HTTPError as e:
            last_error = e
            if e.code not in RETRYABLE_STATUS_CODES or attempt == max_retries:
                break
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(
                f"⚠️  HTTP {e.code} fetching {url} "
                f"(attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
        except (URLError, TimeoutError, socket.timeout) as e:
            last_error = e
            if attempt == max_retries:
                break
            wait_time = retry_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            print(
                f"⚠️  Network error fetching {url}: {e} "
                f"(attempt {attempt}/{max_retries}); retrying in {wait_time:.1f}s..."
            )
            time.sleep(wait_time)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}") from last_error


def load_company_tickers(cache_dir, user_agent, sleep_seconds):
    # Map ticker -> CIK using the SEC company_tickers.json file.
    url = f"{SEC_BASE}/files/company_tickers.json"
    cache_path = os.path.join(cache_dir, "company_tickers.json")
    raw = fetch_url(url, cache_path, user_agent, sleep_seconds)
    data = json.loads(raw.decode("utf-8"))
    mapping = {}
    for entry in data.values():
        ticker = entry.get("ticker")
        cik = entry.get("cik_str")
        title = entry.get("title")
        if not ticker or cik is None:
            continue
        mapping[ticker.upper()] = {"cik": int(cik), "title": title or ""}
    return mapping


def parse_master_idx(text):
    # Parse a quarterly master.idx into structured rows.
    header = "CIK|Company Name|Form Type|Date Filed|Filename"
    lines = text.splitlines()
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == header:
            start_idx = i + 1
            break
    if start_idx is None:
        raise RuntimeError("Unexpected master.idx format; header not found.")

    rows = []
    for line in lines[start_idx:]:
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        cik_str, company, form, date_filed, filename = parts
        rows.append({
            "cik": int(cik_str),
            "company": company,
            "form": form,
            "date_filed": date_filed,
            "filename": filename,
        })
    return rows


def form_matches(form, allowed_forms, include_amends):
    # Include amended filings like 10-Q/A when requested.
    if form in allowed_forms:
        return True
    if include_amends:
        for base in allowed_forms:
            if form.startswith(f"{base}/"):
                return True
    return False


def parse_acceptance_datetime(header):
    # Acceptance timestamp is the most precise "availability" time.
    match = re.search(r"<ACCEPTANCE-DATETIME>\s*(\d{14})", header)
    if not match:
        return None
    dt = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    return dt.replace(tzinfo=SEC_TIMEZONE)


def parse_filing_date(header):
    # Fallback dates when metadata isn't present.
    patterns = [
        r"<FILING-DATE>\s*(\d{8})",
        r"FILED AS OF DATE:\s*(\d{8})",
        r"CONFORMED PERIOD OF REPORT:\s*(\d{8})",
    ]
    for pattern in patterns:
        match = re.search(pattern, header)
        if match:
            d = match.group(1)
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return None


def extract_document_text(content, target_type):
    # Extract the correct <DOCUMENT> block for the filing form.
    documents = content.split("<DOCUMENT>")
    for doc in documents[1:]:
        type_match = re.search(r"<TYPE>\s*([^\n<]+)", doc)
        if not type_match:
            continue
        doc_type = type_match.group(1).strip()
        if doc_type != target_type and not doc_type.startswith(f"{target_type}/"):
            continue
        text_match = re.search(r"<TEXT>(.*)</TEXT>", doc, flags=re.DOTALL | re.IGNORECASE)
        if text_match:
            return text_match.group(1)
    return None


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def load_existing_manifest(manifest_path):
    # Track already downloaded accessions for resumable runs.
    if not os.path.exists(manifest_path):
        return set()
    seen = set()
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                accession = entry.get("accession_number")
                if accession:
                    seen.add(accession)
            except json.JSONDecodeError:
                continue
    return seen


def iter_index_year_quarters(start_date, end_date):
    # end_date is exclusive; only fetch index files that can contain rows in [start_date, end_date).
    last_included_day = end_date - timedelta(days=1)
    for year in range(start_date.year, last_included_day.year + 1):
        for quarter in ("QTR1", "QTR2", "QTR3", "QTR4"):
            yield year, quarter


def main():
    parser = argparse.ArgumentParser(description="Ingest SEC filings via master.idx")
    parser.add_argument("--tickers", default=",".join(DEFAULT_TICKERS))
    parser.add_argument("--forms", default=",".join(DEFAULT_FORMS))
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--cache-dir", default="sec_bulk_index")
    parser.add_argument("--filings-dir", default="sec_bulk_filings")
    parser.add_argument("--manifest", default="sec_bulk_filings/filings_manifest.jsonl")
    parser.add_argument("--user-agent", default=os.getenv("SEC_USER_AGENT"))
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--retry-backoff-seconds", type=float, default=2.0)
    parser.add_argument("--failed-log", default="sec_bulk_filings/failed_downloads.jsonl")
    parser.add_argument("--include-amends", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.user_agent:
        raise SystemExit("Set SEC_USER_AGENT env or pass --user-agent")

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    forms = [f.strip().upper() for f in args.forms.split(",") if f.strip()]
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    if end_date <= start_date:
        raise SystemExit("--end-date must be after --start-date")

    ensure_dir(args.cache_dir)
    ensure_dir(args.filings_dir)

    ticker_map = load_company_tickers(args.cache_dir, args.user_agent, args.sleep_seconds)
    cik_by_ticker = {}
    ticker_by_cik = {}
    for ticker in tickers:
        info = ticker_map.get(ticker)
        if not info:
            print(f"⚠️  Ticker not found in SEC list: {ticker}")
            continue
        cik_by_ticker[ticker] = info["cik"]
        ticker_by_cik[info["cik"]] = ticker

    target_ciks = set(cik_by_ticker.values())
    if not target_ciks:
        raise SystemExit("No valid tickers found; aborting.")

    all_rows = []
    # Pull only the yearly quarter indexes needed for the requested date range.
    for year, qtr in iter_index_year_quarters(start_date, end_date):
        url = f"{SEC_BASE}/Archives/edgar/full-index/{year}/{qtr}/master.idx"
        cache_path = os.path.join(args.cache_dir, f"{year}_{qtr}_master.idx")
        raw = fetch_url(
            url,
            cache_path,
            args.user_agent,
            args.sleep_seconds,
            args.timeout_seconds,
            args.max_retries,
            args.retry_backoff_seconds,
        )
        text = raw.decode("latin-1", errors="ignore")
        all_rows.extend(parse_master_idx(text))

    # Filter by ticker CIK, form type, and date window.
    filtered = []
    for row in all_rows:
        if row["cik"] not in target_ciks:
            continue
        if not form_matches(row["form"], forms, args.include_amends):
            continue
        try:
            filed_date = datetime.strptime(row["date_filed"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (start_date <= filed_date < end_date):
            continue
        filtered.append(row)

    filtered.sort(key=lambda r: (r["cik"], r["date_filed"], r["filename"]))
    if args.limit:
        filtered = filtered[: args.limit]

    seen_accessions = load_existing_manifest(args.manifest)
    matched_accessions = {
        os.path.splitext(os.path.basename(row["filename"]))[0]
        for row in filtered
    }
    already_downloaded = len(matched_accessions & seen_accessions)

    print(f"✅ Rows matched: {len(filtered)}")
    if not filtered:
        return
    if already_downloaded:
        print(f"Resume: skipping {already_downloaded} filings already recorded in {args.manifest}")

    added = 0
    failed = 0
    for row in filtered:
        filename = row["filename"]
        accession = os.path.splitext(os.path.basename(filename))[0]
        if accession in seen_accessions and not args.overwrite:
            continue

        cik = row["cik"]
        ticker = ticker_by_cik.get(cik)
        filing_dir = os.path.join(args.filings_dir, str(cik), accession)
        ensure_dir(filing_dir)
        submission_path = os.path.join(filing_dir, "full-submission.txt")
        metadata_path = os.path.join(filing_dir, "metadata.json")
        document_path = os.path.join(filing_dir, "document.html")

        url = f"{SEC_BASE}/Archives/{filename}"
        try:
            raw = fetch_url(
                url,
                submission_path,
                args.user_agent,
                args.sleep_seconds,
                args.timeout_seconds,
                args.max_retries,
                args.retry_backoff_seconds,
            )
        except RuntimeError as e:
            failed += 1
            print(f"⚠️  {e} -- skipping {accession}")
            append_jsonl(args.failed_log, {
                "accession_number": accession,
                "ticker": ticker,
                "form": row["form"],
                "source_url": url,
                "error": str(e),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            })
            continue
        content = raw.decode("latin-1", errors="ignore")
        header = content[:20000]

        acceptance_dt = parse_acceptance_datetime(header)
        filing_date = parse_filing_date(header) or row["date_filed"]
        document_text = extract_document_text(content, row["form"])
        if not document_text:
            print(f"⚠️  No <TEXT> for {accession} ({row['form']}); skipping")
            continue

        # Save the extracted filing body and metadata for downstream chunking.
        with open(document_path, "w", encoding="utf-8") as f:
            f.write(document_text)

        metadata = {
            "ticker": ticker,
            "cik": cik,
            "company": row["company"],
            "form": row["form"],
            "date_filed": row["date_filed"],
            "filing_date": filing_date,
            "acceptance_datetime": acceptance_dt.astimezone(timezone.utc).isoformat() if acceptance_dt else None,
            "accession_number": accession,
            "filename": filename,
            "source_url": url,
            "submission_path": submission_path,
            "document_path": document_path,
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=True)

        with open(args.manifest, "a", encoding="utf-8") as f:
            f.write(json.dumps(metadata, ensure_ascii=True) + "\n")

        added += 1
        seen_accessions.add(accession)
        if added % 25 == 0:
            print(f"  ... downloaded {added} filings")

    print(f"✅ Downloaded {added} filings to {args.filings_dir}")
    if failed:
        print(f"⚠️  Skipped {failed} filings after retries; see {args.failed_log}")


if __name__ == "__main__":
    main()
