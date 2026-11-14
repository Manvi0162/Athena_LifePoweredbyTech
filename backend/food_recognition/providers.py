"""Vision providers. The API key is read server-side only and never sent to the app."""

import base64
import json
import os
from typing import Protocol

import httpx

PROMPT = """You identify food in a photo for a household pantry app in Mauritius.

Rules:
- List each distinct food item you can see (fresh produce, or packaged food/drink).
- category: "fresh" for unpackaged produce or meat/fish, "packaged" for anything in a
  wrapper, tin, bottle or box, "unknown" if you cannot tell.
- name: a plain generic name (e.g. "carrot", "rice", "tomato sauce"). Do not guess brands
  you cannot read.
- confidence: a number from 0 to 1. Be conservative. Use below 0.5 if unsure.
- label_text: any readable words on the packaging, copied exactly, max 20 entries.
- Do not estimate prices, nutrition, weight or expiry dates.
- If there is no food, return an empty items list.

Respond with JSON only, in this shape:
{"items":[{"name":"...","category":"fresh|packaged|unknown","confidence":0.0,"label_text":[]}],"message":""}"""


class VisionProvider(Protocol):
    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        """Return the model's raw text reply (expected to be JSON)."""


class AnthropicVisionProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
        self.model = model or os.environ.get("FOOD_VISION_MODEL", "claude-haiku-5-5")
        self.base_url = (base_url or os.environ.get("ANTHROPIC_BASE_URL")
                         or "https://api.anthropic.com").rstrip("/")
        self.timeout = timeout

    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        body = {
            "model": self.model,
            "max_tokens": 800,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                    }},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/v1/messages", headers=headers, json=body)
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
