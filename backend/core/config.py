"""Settings read from environment variables. Nothing secret is sent to the app."""

import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        # Same rule as the notebook: only the publishable key. The user's own
        # login token is attached per request, so row-level security applies.
        self.supabase_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
        if self.supabase_key and not self.supabase_key.startswith("sb_publishable_"):
            raise RuntimeError("SUPABASE_PUBLISHABLE_KEY must be a publishable key "
                               "(sb_publishable_...). Never use the secret key here.")
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        # Same order as MODEL_CANDIDATES in the notebook's recipe engine.
        self.gemini_text_models = [m.strip() for m in os.environ.get(
            "GEMINI_TEXT_MODELS",
            "gemini-3.1-flash-lite,gemini-3.5-flash-lite,gemini-3.8-flash",
        ).split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
