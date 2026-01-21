import os
from typing import List, Dict, Optional

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client

_MODEL = None


def _get_model(model_name: str, device: str):
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(model_name, device=device)
    return _MODEL


def _get_supabase_client() -> Client:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(supabase_url, supabase_key)


def retrieve_filings(
    query: str,
    ticker: str,
    as_of: str,
    match_threshold: float = 0.3,
    model_name: str = "intfloat/e5-base-v2",
    device: str = "cpu",
    normalize: bool = True,
) -> List[Dict]:
    model = _get_model(model_name, device)
    vector = model.encode(
        [query],
        normalize_embeddings=normalize,
        show_progress_bar=False,
    )[0].tolist()

    supabase = _get_supabase_client()
    res = supabase.rpc(
        "search_knowledge_base",
        {
            "query_embedding": vector,
            "match_threshold": match_threshold,
            "filter_time": as_of,
            "filter_ticker": ticker,
        },
    ).execute()
    return res.data or []
