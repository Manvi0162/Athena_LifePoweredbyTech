"""Google AI Studio (Gemini API) vision provider with model fallback.

Tries each model in order. A busy model (429/500/503) gets one quick retry, then
the next model is tried. A missing model (404) is skipped straight away.
Key is read server-side only.
"""

import asyncio
import base64
import logging
import os

import httpx

from .providers import PROMPT

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
BUSY_STATUSES = {429, 500, 503}
SKIP_STATUSES = {404}
DEFAULT_MODELS = "gemini-3.1-flash-lite,gemini-3.6-flash"  # flash-lite: reliable in the notebook


class GeminiVisionProvider:
    def __init__(self, api_key: str | None = None, models: list[str] | None = None,
                 timeout: float = 15.0, retry_delay: float = 2.0,
                 transport: httpx.AsyncBaseTransport | None = None):
        self.api_key = api_key or os.environ["GEMINI_API_KEY"]
        if models is None:
            raw = os.environ.get("GEMINI_VISION_MODELS", DEFAULT_MODELS)
            models = [m.strip() for m in raw.split(",") if m.strip()]
        self.models = models
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.transport = transport

    def _body(self, image_bytes: bytes, media_type: str) -> dict:
        return {
            "contents": [{
                "parts": [
                    {"inline_data": {
                        "mime_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                    }},
                    {"text": PROMPT},
                ],
            }],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json",
            },
        }

    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        body = self._body(image_bytes, media_type)
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        last_error = "no models configured"

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            for model in self.models:
                url = GEMINI_URL.format(model=model)
                for attempt in range(2):  # first try + one retry if busy
                    try:
                        resp = await client.post(url, headers=headers, json=body)
                    except httpx.TransportError as exc:  # timeout, dropped connection
                        last_error = f"{model}: {type(exc).__name__}"
                        log.warning("Gemini %s did not respond (%s), trying next model",
                                    model, type(exc).__name__)
                        break
                    if resp.status_code == 200:
                        log.info("Gemini answered with model %s", model)
                        parts = resp.json()["candidates"][0]["content"]["parts"]
                        return "".join(p.get("text", "") for p in parts)
                    last_error = f"{model}: {resp.status_code} {resp.text[:200]}"
                    if resp.status_code in BUSY_STATUSES and attempt == 0:
                        log.warning("Gemini %s busy (%s), retrying once", model, resp.status_code)
                        await asyncio.sleep(self.retry_delay)
                        continue
                    if resp.status_code in BUSY_STATUSES | SKIP_STATUSES:
                        log.warning("Gemini %s unavailable (%s), trying next model",
                                    model, resp.status_code)
                        break
                    # 400/401/403 etc.: a key or request problem the next model won't fix.
                    log.error("Gemini error: %s", last_error)
                    resp.raise_for_status()

        raise RuntimeError(f"All Gemini models unavailable. Last error: {last_error}")
