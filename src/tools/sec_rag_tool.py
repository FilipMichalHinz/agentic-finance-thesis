import os
from typing import Optional, List, Dict

from langchain_core.tools import tool

from src.integrations.sec_rag import retrieve_filings


@tool("search_filings")
def search_filings(
    query: str,
    ticker: str,
    as_of: str,
    match_threshold: float = 0.3,
    device: str = "cpu",
) -> List[Dict]:
    """
    Search SEC filings for a ticker up to a given timestamp.
    Returns a list of {content, similarity, published_at, source_type}.
    """
    device_norm = device.strip().lower()
    if device_norm not in {"cpu", "mps", "cuda"}:
        device_norm = "cpu"
    return retrieve_filings(
        query=query,
        ticker=ticker,
        as_of=as_of,
        match_threshold=match_threshold,
        provider=os.getenv("EMBEDDING_PROVIDER", "gemini"),
        gemini_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
        device=device_norm,
    )
