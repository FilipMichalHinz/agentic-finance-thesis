#!/usr/bin/env python3
import argparse
import os

from dotenv import load_dotenv
from supabase import create_client, Client


def parse_args():
    parser = argparse.ArgumentParser(description="Test time-gated retrieval from Supabase")
    parser.add_argument("--query", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--time", required=True, help="ISO timestamp, e.g. 2024-08-01T00:00:00Z")
    parser.add_argument("--match-threshold", type=float, default=0.3)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--provider", choices=["gemini", "local"], default=os.getenv("EMBEDDING_PROVIDER", "gemini"))
    parser.add_argument("--gemini-model", default=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"))
    parser.add_argument("--model", default="intfloat/e5-base-v2")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--normalize", action="store_true", default=True)
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

    supabase: Client = create_client(supabase_url, supabase_key)
    if args.provider == "gemini":
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            raise SystemExit("Set GOOGLE_API_KEY")
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=google_key)
        response = client.models.embed_content(
            model=args.gemini_model,
            contents=[args.query],
            config=types.EmbedContentConfig(
                output_dimensionality=768,
                task_type="RETRIEVAL_QUERY",
            ),
        )
        query_vector = response.embeddings[0].values
    else:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(args.model, device=args.device)
        query_vector = model.encode(
            [args.query],
            normalize_embeddings=args.normalize,
            show_progress_bar=False,
        )[0].tolist()

    res = supabase.rpc(
        "search_knowledge_base",
        {
            "query_embedding": query_vector,
            "match_threshold": args.match_threshold,
            "filter_time": args.time,
            "filter_ticker": args.ticker,
        },
    ).execute()

    rows = res.data or []
    if not rows:
        print("No results")
        return

    print(f"Results ({len(rows)}):")
    for i, row in enumerate(rows, start=1):
        snippet = row["content"].replace("\n", " ")[:200]
        print(f"{i}. {row['published_at']} | {row['source_type']} | sim={row['similarity']:.3f}")
        print(f"   {snippet}...")


if __name__ == "__main__":
    main()
