from typing import List, Dict, Optional

from dotenv import load_dotenv

from src.integrations.google_genai import build_genai_client, embed_texts
from src.integrations.supabase_client import get_supabase_client

_MODEL = None
_GEMINI_CLIENT = None


def _get_model(model_name: str, device: str):
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(model_name, device=device)
    return _MODEL


def _get_gemini_client(timeout_seconds: int):
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        load_dotenv()
        _GEMINI_CLIENT = build_genai_client(timeout_seconds=timeout_seconds)
    return _GEMINI_CLIENT


def retrieve_filings(
    query: str,
    ticker: str,
    as_of: str,
    match_threshold: float = 0.3,
    provider: str = "gemini",
    gemini_model: str = "gemini-embedding-001",
    model_name: str = "intfloat/e5-base-v2",
    device: str = "cpu",
    normalize: bool = True,
    timeout_seconds: int = 300,
) -> List[Dict]:
    provider_norm = provider.strip().lower()
    if provider_norm == "gemini":
        client = _get_gemini_client(timeout_seconds)
        vectors = embed_texts(
            client,
            [query],
            model_name=gemini_model,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        )
        vector = vectors[0]
    else:
        model = _get_model(model_name, device)
        vector = model.encode(
            [query],
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )[0].tolist()

    supabase = get_supabase_client()
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
