"""Groq vision provider (free tier). Key is read server-side only."""

import base64
import os

import httpx

from .providers import PROMPT

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqVisionProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 timeout: float = 20.0):
        self.api_key = api_key or os.environ["GROQ_API_KEY"]
        # Confirm the exact model ID in the Groq console at kickoff; override with GROQ_VISION_MODEL.
        self.model = model or os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
        self.timeout = timeout

    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        data_url = f"data:{media_type};base64,{base64.standard_b64encode(image_bytes).decode('ascii')}"
        body = {
            "model": self.model,
            "max_tokens": 800,
            "temperature": 0,
            "response_format": {"type": "json_object"},
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
            resp = await client.post(GROQ_URL, headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
