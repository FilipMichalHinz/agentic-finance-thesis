#!/usr/bin/env python3
import argparse
import json
import os

from dotenv import load_dotenv
from supabase import Client, create_client


def parse_args():
    parser = argparse.ArgumentParser(description="Ingest SEC filing events from the local manifest into Supabase")
    parser.add_argument("--manifest", default="sec_bulk_filings/filings_manifest.jsonl")
    parser.add_argument("--db-batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def build_row(payload):
    return {
        "ticker": payload.get("ticker"),
        "cik": payload.get("cik"),
        "company_name": payload.get("company"),
        "form": payload.get("form"),
        "filing_date": payload.get("filing_date") or payload.get("date_filed"),
        "acceptance_datetime": payload.get("acceptance_datetime"),
        "accession_number": payload.get("accession_number"),
        "filename": payload.get("filename"),
        "source_url": payload.get("source_url"),
        "submission_path": payload.get("submission_path"),
        "document_path": payload.get("document_path"),
    }


def flush_batch(supabase: Client, rows):
    if not rows:
        return
    supabase.table("sec_filing_events").upsert(
        rows,
        on_conflict="accession_number",
    ).execute()


def main():
    args = parse_args()
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    if not os.path.exists(args.manifest):
        raise SystemExit(f"Manifest not found: {args.manifest}")

    supabase: Client = create_client(supabase_url, supabase_key)

    print("🚀 Starting SEC filing event ingestion...")
    pending_rows = []
    total = 0
    with open(args.manifest, "r", encoding="utf-8") as f:
        for line in f:
            if args.limit and total >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            accession_number = payload.get("accession_number")
            if not accession_number:
                continue

            pending_rows.append(build_row(payload))
            total += 1

            if len(pending_rows) >= args.db_batch_size:
                flush_batch(supabase, pending_rows)
                print(f"  ... upserted {total} filing events")
                pending_rows = []

    flush_batch(supabase, pending_rows)
    print(f"🏁 SEC filing event ingestion complete. Upserted {total} events.")


if __name__ == "__main__":
    main()
