import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from core.auth import get_user_context

from .fallback import FallbackProvider
from .gemini_provider import GeminiVisionProvider
from .groq_provider import GroqVisionProvider
from .openrouter_provider import OpenRouterVisionProvider
from .providers import AnthropicVisionProvider, VisionProvider
from .schemas import RecognitionResult
from .service import ImageRejected, MAX_BYTES, recognise_food

log = logging.getLogger(__name__)
# Login required, so nobody can use up the free AI quota anonymously.
router = APIRouter(prefix="/food", tags=["food"], dependencies=[Depends(get_user_context)])

# name -> (provider class, env var holding its key)
PROVIDERS = {
    "gemini": (GeminiVisionProvider, "GEMINI_API_KEY"),
    "groq": (GroqVisionProvider, "GROQ_API_KEY"),
    "openrouter": (OpenRouterVisionProvider, "OPENROUTER_API_KEY"),
    "anthropic": (AnthropicVisionProvider, "ANTHROPIC_API_KEY"),  # paid, off by default
}

_provider: VisionProvider | None = None


def build_provider() -> VisionProvider:
    """Chain providers in FOOD_VISION_PROVIDERS order (default: groq,gemini,openrouter).
    A provider is only included if its API key is set."""
    order = os.environ.get("FOOD_VISION_PROVIDERS", "groq,gemini,openrouter")
    chain = []
    for name in (n.strip().lower() for n in order.split(",")):
        if name in PROVIDERS and os.environ.get(PROVIDERS[name][1]):
            chain.append(PROVIDERS[name][0]())
    if not chain:
        raise RuntimeError("No vision provider has an API key set (e.g. GEMINI_API_KEY)")
    log.info("Vision providers in order: %s", [type(p).__name__ for p in chain])
    return FallbackProvider(chain)


def get_provider() -> VisionProvider:
    global _provider
    if _provider is None:
        _provider = build_provider()
    return _provider


@router.post("/recognize", response_model=RecognitionResult)
async def recognize(image: UploadFile = File(...),
                    provider: VisionProvider = Depends(get_provider)):
    data = await image.read(MAX_BYTES + 1)
    try:
        return await recognise_food(data, provider)
    except ImageRejected as exc:
        raise HTTPException(status_code=422, detail={"code": "bad_image", "message": str(exc)})
    except Exception:  # every provider failed: outage, timeout, bad key
        log.exception("Vision provider failed")
        raise HTTPException(status_code=503, detail={
            "code": "vision_unavailable",
            "message": "Photo recognition is unavailable right now. Add items manually.",
        })
