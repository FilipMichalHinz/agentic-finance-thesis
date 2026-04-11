#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from postgrest.exceptions import APIError
from supabase import create_client, Client

try:
    from src.integrations.google_genai import build_genai_client, embed_texts
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.integrations.google_genai import build_genai_client, embed_texts


def parse_args():
    parser = argparse.ArgumentParser(description="Embed knowledge_base rows missing embeddings")
    parser.add_argument("--provider", choices=["gemini", "local"], default="gemini")
    parser.add_argument("--gemini-model", default=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"))
    parser.add_argument("--local-model", default="intfloat/e5-base-v2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--normalize", action="store_true", default=True)
    parser.add_argument("--embed-batch-size", type=int, default=5)
    parser.add_argument("--db-batch-size", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--ticker", default="")
    parser.add_argument("--log-file", default="sec_bulk_filings/failed_embeddings.jsonl")
    return parser.parse_args()


def log_failed_embedding(path, payload):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception as e:
        print(f"⚠️  Failed to log embedding failure: {e}")


def render_progress(processed, total, bar_width=30, estimated_total=False):
    if total is None:
        print(f"\rProgress: {processed} rows", end="", flush=True)
        return
    if total <= 0:
        print("\rProgress: 0/0", end="", flush=True)
        return
    ratio = min(max(processed / total, 0.0), 1.0)
    filled = int(bar_width * ratio)
    bar = "#" * filled + "-" * (bar_width - filled)
    if estimated_total:
        print(f"\rProgress: [{bar}] {processed}/{total} (est.)", end="", flush=True)
    else:
        print(f"\rProgress: [{bar}] {processed}/{total}", end="", flush=True)


def get_batch_embeddings_gemini(client, model_name, texts, max_retries, sleep_seconds):
    if not texts:
        return []
    for attempt in range(max_retries):
        try:
            return embed_texts(
                client,
                texts,
                model_name=model_name,
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768,
            )
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            if status_code is None:
                status_code = getattr(e, "code", None)
            if status_code is not None and 400 <= status_code < 500 and status_code != 429:
                raise
            wait_time = (attempt + 1) * 2 + random.uniform(0.5, 1.5)
            print(f"⚠️  API Error (Attempt {attempt+1}/{max_retries}): {e} - Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
    print("❌ Failed to embed batch after retries.")
    return [None] * len(texts)


def get_batch_embeddings_local(model, texts, normalize):
    if not texts:
        return []
    vectors = model.encode(
        texts,
        normalize_embeddings=normalize,
        show_progress_bar=False,
    )
    return vectors.tolist()


def is_statement_timeout(exc):
    code = getattr(exc, "code", None)
    message = getattr(exc, "message", "") or ""
    details = getattr(exc, "details", "") or ""
    text = f"{message} {details}".lower()
    return code == "57014" or "statement timeout" in text


def upsert_updates_with_retry(supabase: Client, updates):
    if not updates:
        return
    try:
        supabase.table("knowledge_base").upsert(updates, on_conflict="id").execute()
    except APIError as exc:
        if not is_statement_timeout(exc) or len(updates) == 1:
            raise
        midpoint = len(updates) // 2
        print(
            f"\n⚠️ statement timeout on embedding update batch of {len(updates)} rows; "
            f"splitting into {midpoint} and {len(updates) - midpoint}"
        )
        upsert_updates_with_retry(supabase, updates[:midpoint])
        upsert_updates_with_retry(supabase, updates[midpoint:])


def fetch_remaining_count(supabase: Client, ticker: str):
    count_query = (
        supabase.table("knowledge_base")
        .select("id", count="planned")
        .is_("embedding", "null")
    )
    if ticker:
        count_query = count_query.eq("ticker", ticker)
    try:
        return (count_query.execute().count or 0), True
    except APIError as exc:
        if is_statement_timeout(exc):
            print("⚠️ remaining-row count timed out; continuing without a total progress estimate")
            return None, False
        raise


def fetch_pending_rows(supabase: Client, batch_limit: int, last_id: int, ticker: str):
    try:
        query = (
            supabase.table("knowledge_base")
            .select("id, content, ticker, source_type, published_at")
            .is_("embedding", "null")
            .gt("id", last_id)
            .order("id")
            .limit(batch_limit)
        )
        if ticker:
            query = query.eq("ticker", ticker)
        return query.execute().data or []
    except APIError as exc:
        if not is_statement_timeout(exc) or batch_limit == 1:
            raise
        smaller_limit = max(1, batch_limit // 2)
        print(
            f"\n⚠️ read query timed out at batch size {batch_limit}; "
            f"retrying with {smaller_limit}"
        )
        return fetch_pending_rows(supabase, smaller_limit, last_id, ticker)


def main():
    args = parse_args()
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    supabase: Client = create_client(supabase_url, supabase_key)

    embed_fn = None
    if args.provider == "gemini":
        client = build_genai_client(timeout_seconds=args.timeout_seconds)
        embed_fn = lambda texts: get_batch_embeddings_gemini(  # noqa: E731
            client, args.gemini_model, texts, args.max_retries, args.sleep_seconds
        )
    elif args.provider == "local":
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(args.local_model, device=args.device)
        embed_fn = lambda texts: get_batch_embeddings_local(  # noqa: E731
            model, texts, args.normalize
        )
    else:
        raise SystemExit(f"Unknown provider: {args.provider}")

    total_remaining, estimated_total = fetch_remaining_count(supabase, args.ticker)

    processed = 0
    last_id = 0
    render_progress(processed, total_remaining, estimated_total=estimated_total)
    while True:
        remaining = args.limit - processed if args.limit else None
        batch_limit = min(args.db_batch_size, remaining) if remaining else args.db_batch_size

        rows = fetch_pending_rows(supabase, batch_limit, last_id, args.ticker)
        if not rows:
            break

        last_id = rows[-1]["id"]

        updates = []
        for i in range(0, len(rows), args.embed_batch_size):
            batch_rows = rows[i : i + args.embed_batch_size]
            texts = [r["content"] for r in batch_rows]
            vectors = embed_fn(texts)
            if vectors and len(vectors[0]) != 768:
                raise SystemExit(f"Embedding dim {len(vectors[0])} != 768; update model or schema.")
            for row, vector in zip(batch_rows, vectors):
                published_at = row.get("published_at")
                if vector and published_at:
                    updates.append({
                        "id": row["id"],
                        "embedding": vector,
                        "published_at": published_at,
                    })
                else:
                    log_failed_embedding(args.log_file, {
                        "id": row["id"],
                        "ticker": row.get("ticker"),
                        "source_type": row.get("source_type"),
                        "published_at": published_at,
                    })
            time.sleep(args.sleep_seconds)

        if updates:
            upsert_updates_with_retry(supabase, updates)

        processed += len(rows)
        render_progress(processed, total_remaining, estimated_total=estimated_total)
        if args.limit and processed >= args.limit:
            break

    print()
    print(f"✅ Embedded {processed} rows")


if __name__ == "__main__":
    main()
