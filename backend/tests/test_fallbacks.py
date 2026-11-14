import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from food_recognition import router as router_mod  # noqa: E402
from food_recognition.fallback import FallbackProvider  # noqa: E402
from food_recognition.gemini_provider import GeminiVisionProvider  # noqa: E402

OK_BODY = {"candidates": [{"content": {"parts": [{"text": '{"items":[]}'}]}}]}


def run(coro):
    return asyncio.run(coro)


def gemini_with(responses: dict[str, list[int]]):
    """responses: model -> list of status codes returned in order."""
    calls = []

    def handler(request: httpx.Request):
        model = request.url.path.split("/models/")[1].split(":")[0]
        calls.append(model)
        status = responses[model].pop(0)
        return httpx.Response(status, json=OK_BODY if status == 200 else {"error": {}})

    provider = GeminiVisionProvider(api_key="k", models=list(responses), retry_delay=0,
                                    transport=httpx.MockTransport(handler))
    return provider, calls


def test_gemini_falls_back_to_second_model_when_first_is_busy():
    provider, calls = gemini_with({"m1": [503, 503], "m2": [200]})
    assert run(provider.describe(b"x", "image/jpeg")) == '{"items":[]}'
    assert calls == ["m1", "m1", "m2"]


def test_gemini_retry_succeeds_on_same_model():
    provider, calls = gemini_with({"m1": [503, 200], "m2": []})
    run(provider.describe(b"x", "image/jpeg"))
    assert calls == ["m1", "m1"]


def test_gemini_skips_missing_model_without_retry():
    provider, calls = gemini_with({"m1": [404], "m2": [200]})
    run(provider.describe(b"x", "image/jpeg"))
    assert calls == ["m1", "m2"]


def test_gemini_timeout_moves_to_next_model():
    calls = []

    def handler(request: httpx.Request):
        model = request.url.path.split("/models/")[1].split(":")[0]
        calls.append(model)
        if model == "m1":
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json=OK_BODY)

    provider = GeminiVisionProvider(api_key="k", models=["m1", "m2"], retry_delay=0,
                                    transport=httpx.MockTransport(handler))
    assert run(provider.describe(b"x", "image/jpeg")) == '{"items":[]}'
    assert calls == ["m1", "m2"]


def test_gemini_bad_key_stops_immediately():
    provider, calls = gemini_with({"m1": [403], "m2": [200]})
    with pytest.raises(httpx.HTTPStatusError):
        run(provider.describe(b"x", "image/jpeg"))
    assert calls == ["m1"]


def test_gemini_all_models_busy_raises():
    provider, _ = gemini_with({"m1": [503, 503], "m2": [503, 503]})
    with pytest.raises(RuntimeError):
        run(provider.describe(b"x", "image/jpeg"))


class Fake:
    def __init__(self, reply=None):
        self.reply = reply

    async def describe(self, image_bytes, media_type):
        if self.reply is None:
            raise RuntimeError("down")
        return self.reply


def test_fallback_uses_next_provider():
    assert run(FallbackProvider([Fake(), Fake("ok")]).describe(b"x", "image/jpeg")) == "ok"


def test_fallback_raises_when_all_fail():
    with pytest.raises(RuntimeError):
        run(FallbackProvider([Fake(), Fake()]).describe(b"x", "image/jpeg"))


def test_chain_only_includes_providers_with_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("FOOD_VISION_PROVIDERS", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    chain = router_mod.build_provider()
    assert [type(p).__name__ for p in chain.providers] == ["GeminiVisionProvider"]

    monkeypatch.setenv("GROQ_API_KEY", "g")
    chain = router_mod.build_provider()
    # Groq first (fast, higher free limit), Gemini as fallback.
    assert [type(p).__name__ for p in chain.providers] == ["GroqVisionProvider",
                                                          "GeminiVisionProvider"]
