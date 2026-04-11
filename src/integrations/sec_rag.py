import os
from typing import List, Dict, Optional

from dotenv import load_dotenv

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
        google_key = os.getenv("GOOGLE_API_KEY")
        if not google_key:
            raise RuntimeError("Missing GOOGLE_API_KEY")
        from google import genai
        _GEMINI_CLIENT = genai.Client(api_key=google_key, http_options={"timeout": int(timeout_seconds * 1000)})
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
        from google.genai import types
        client = _get_gemini_client(timeout_seconds)
        response = client.models.embed_content(
            model=gemini_model,
            contents=[query],
            config=types.EmbedContentConfig(
                output_dimensionality=768,
                task_type="RETRIEVAL_QUERY",
            ),
        )
        vector = response.embeddings[0].values
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
