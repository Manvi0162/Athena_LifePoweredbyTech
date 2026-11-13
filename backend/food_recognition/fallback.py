"""Tries vision providers in order until one answers."""

import logging

log = logging.getLogger(__name__)


class FallbackProvider:
    def __init__(self, providers: list):
        if not providers:
            raise ValueError("At least one vision provider is required")
        self.providers = providers

    async def describe(self, image_bytes: bytes, media_type: str) -> str:
        last_exc: Exception | None = None
        for provider in self.providers:
            name = type(provider).__name__
            try:
                return await provider.describe(image_bytes, media_type)
            except Exception as exc:
                log.warning("%s failed (%r), trying next provider", name, exc)
                last_exc = exc
        raise RuntimeError("All vision providers failed") from last_exc
