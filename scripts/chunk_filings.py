#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from supabase import create_client, Client


def parse_args():
    parser = argparse.ArgumentParser(description="Chunk SEC filings and store in Supabase")
    parser.add_argument("--manifest", default="sec_bulk_filings/filings_manifest.jsonl")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--db-batch-size", type=int, default=200)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def normalize_published_at(metadata):
    acceptance = metadata.get("acceptance_datetime")
    if acceptance:
        return acceptance
    filing_date = metadata.get("filing_date") or metadata.get("date_filed")
    if filing_date:
        return f"{filing_date}T00:00:00Z"
    return None


def load_document_text(document_path):
    with open(document_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def html_to_chunks(html_text, chunk_size, chunk_overlap):
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator="\n")
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_text(text)


def main():
    args = parse_args()
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    supabase: Client = create_client(supabase_url, supabase_key)

    if not os.path.exists(args.manifest):
        raise SystemExit(f"Manifest not found: {args.manifest}")

    total = 0
    pending_rows = []
    with open(args.manifest, "r", encoding="utf-8") as f:
        for line in f:
            if args.limit and total >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                metadata = json.loads(line)
            except json.JSONDecodeError:
                continue

            document_path = metadata.get("document_path")
            if not document_path or not os.path.exists(document_path):
                print(f"⚠️ Missing document: {document_path}")
                continue

            published_at = normalize_published_at(metadata)
            if not published_at:
                print(f"⚠️ Missing published_at for {document_path}; skipping")
                continue

            html_text = load_document_text(document_path)
            chunks = html_to_chunks(html_text, args.chunk_size, args.chunk_overlap)
            if not chunks:
                continue

            ticker = metadata.get("ticker")
            source_type = metadata.get("form")
            accession_number = metadata.get("accession_number")
            source_url = metadata.get("source_url")
            filing_date = metadata.get("filing_date") or metadata.get("date_filed")
            acceptance_dt = metadata.get("acceptance_datetime")

            for i, chunk_text in enumerate(chunks):
                pending_rows.append({
                    "ticker": ticker,
                    "title": f"{ticker} {source_type} ({filing_date}) Pt-{i}",
                    "content": chunk_text,
                    "published_at": published_at,
                    "source_type": source_type,
                    "accession_number": accession_number,
                    "chunk_index": i,
                    "acceptance_datetime": acceptance_dt,
                    "filing_date": filing_date,
                    "source_url": source_url,
                })

                if len(pending_rows) >= args.db_batch_size:
                    supabase.table("knowledge_base").upsert(
                        pending_rows,
                        on_conflict="accession_number,chunk_index"
                    ).execute()
                    pending_rows = []
            total += 1

    if pending_rows:
        supabase.table("knowledge_base").upsert(
            pending_rows,
            on_conflict="accession_number,chunk_index"
        ).execute()

    print(f"✅ Chunked and stored {total} filings")


if __name__ == "__main__":
    main()
