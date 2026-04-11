import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

_SUPABASE_CLIENT: Optional[Client] = None


def get_supabase_client() -> Client:
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is None:
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT
