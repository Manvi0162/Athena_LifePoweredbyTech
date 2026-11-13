"""OpenRouter vision provider (free models). Key is read server-side only."""

import base64
import os

import httpx

from .providers import PROMPT

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterVisionProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 timeout: float = 20.0):
        self.api_key = api_key or os.environ["OPENROUTER_API_KEY"]
        # "openrouter/free" routes to a free model that supports images.
        # Override with OPENROUTER_VISION_MODEL (pick one ending in ":free" to stay free).
        self.model = model or os.environ.get("OPENROUTER_VISION_MODEL", "openrouter/free")
        self.timeout = timeout

    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        data_url = f"data:{media_type};base64,{base64.standard_b64encode(image_bytes).decode('ascii')}"
        body = {
            "model": self.model,
            "max_tokens": 800,
            "temperature": 0,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(OPENROUTER_URL, headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
