"""
Lightweight Supabase client used for structured logging and long-term memory.
Kept separate from the MAS graph so we can swap storage later without touching agents.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from supabase import Client, create_client
except ImportError:  # pragma: no cover - optional dependency
    Client = None  # type: ignore
    create_client = None  # type: ignore


class SupabaseLogger:
    """
    Thin wrapper around Supabase tables:
    - agent_events: per-agent logs (decision traces, messages, scores, etc.)
    - agent_memory: long-term notes, summaries, embeddings (future use)
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        table_events: str = "agent_events",
        table_memory: str = "agent_memory",
    ) -> None:
        url = url or os.getenv("SUPABASE_URL")
        key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not url or not key or not create_client:
            # Keep the rest of the system running even if Supabase is absent.
            self.client = None
        else:
            self.client: Client = create_client(url, key)
        self.table_events = table_events
        self.table_memory = table_memory

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def _utc_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_event(
        self,
        run_id: str,
        agent: str,
        stage: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Store a single agent message/decision. Payload is free-form JSON.
        """
        if not self.enabled:
            return
        record = {
            "run_id": run_id,
            "agent": agent,
            "stage": stage,
            "payload": payload,
            "created_at": self._utc_timestamp(),
        }
        # Fire-and-forget; errors bubble up only for debugging.
        self.client.table(self.table_events).insert(record).execute()  # type: ignore[attr-defined]

    def store_memory(
        self,
        run_id: str,
        topic: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist longer-lived memory (summaries, retrieved docs, embeddings later).
        """
        if not self.enabled:
            return
        record = {
            "run_id": run_id,
            "topic": topic,
            "content": content,
            "metadata": metadata or {},
            "created_at": self._utc_timestamp(),
        }
        self.client.table(self.table_memory).insert(record).execute()  # type: ignore[attr-defined]
