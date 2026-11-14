"""Gemini text + image calls with the same model fallback as the notebook's
`gemini_generate`: a busy model gets one retry, a missing model is skipped,
any other error (bad key, bad request) stops immediately."""

import base64
import logging
import random
import time

import httpx

from .config import get_settings

log = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TRANSIENT = {429, 500, 503, 504}
SKIP = {404}


class LLMUnavailable(RuntimeError):
    pass


def image_part(data: bytes, mime_type: str) -> dict:
    return {"inline_data": {"mime_type": mime_type,
                            "data": base64.standard_b64encode(data).decode("ascii")}}


def gemini_generate(parts: list, json_output: bool = True, temperature: float = 0.2,
                    models: list[str] | None = None, api_key: str | None = None,
                    transport: httpx.BaseTransport | None = None,
                    retry_delay: float | None = None) -> str:
    settings = get_settings()
    models = models or settings.gemini_text_models
    api_key = api_key or settings.gemini_api_key
    body = {
        "contents": [{"parts": [{"text": p} if isinstance(p, str) else p for p in parts]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json" if json_output else "text/plain",
        },
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    errors = []

    with httpx.Client(timeout=30.0, transport=transport) as client:
        for model in models:
            for attempt in range(2):
                try:
                    resp = client.post(GEMINI_URL.format(model=model), headers=headers, json=body)
                except httpx.TransportError as exc:
                    errors.append(f"{model}: {type(exc).__name__}")
                    break  # timeout or dropped connection: try the next model
                if resp.status_code == 200:
                    parts_out = resp.json()["candidates"][0]["content"].get("parts", [])
                    text = "".join(p.get("text", "") for p in parts_out)
                    if not text:
                        errors.append(f"{model}: empty response")
                        break
                    log.info("Gemini model used: %s", model)
                    return text
                errors.append(f"{model}: {resp.status_code} {resp.text[:140]}")
                if resp.status_code in TRANSIENT and attempt == 0:
                    time.sleep(retry_delay if retry_delay is not None else 2 + random.random())
                    continue
                if resp.status_code in TRANSIENT | SKIP:
                    break
                raise LLMUnavailable("Gemini request rejected: " + errors[-1])
    raise LLMUnavailable("No Gemini model available. " + " | ".join(errors))
