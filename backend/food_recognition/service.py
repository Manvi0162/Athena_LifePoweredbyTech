import json
import re

from .providers import VisionProvider
from .schemas import RecognisedItem, RecognitionResult

MAX_BYTES = 5 * 1024 * 1024
LOW_CONFIDENCE = 0.5

# Magic bytes -> media type. Only these formats are accepted.
_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),  # confirmed below: bytes 8..12 must be WEBP
]


class ImageRejected(ValueError):
    pass


def detect_media_type(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ImageRejected("Image is larger than 5 MB. Please retake or resize it.")
    for sig, media in _SIGNATURES:
        if data.startswith(sig):
            if media == "image/webp" and data[8:12] != b"WEBP":
                continue
            return media
    raise ImageRejected("Unsupported image type. Use JPEG, PNG or WebP.")


def parse_model_reply(raw: str) -> RecognitionResult:
    """Parse the model's JSON reply. Anything malformed becomes an empty result
    with a message, so the app falls back to manual entry instead of crashing."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return RecognitionResult(message="Could not read the photo. Please add items manually.")
    try:
        data = json.loads(match.group(0))
        items = []
        for raw_item in data.get("items", [])[:10]:
            item = RecognisedItem(**{k: raw_item[k] for k in
                                     ("name", "category", "confidence", "label_text")
                                     if k in raw_item})
            item.low_confidence = item.confidence < LOW_CONFIDENCE
            items.append(item)
        message = str(data.get("message", ""))
    except (ValueError, TypeError, KeyError):
        return RecognitionResult(message="Could not read the photo. Please add items manually.")

    if not items:
        message = message or "No food recognised. Try a closer, brighter photo or add items manually."
    elif all(i.low_confidence for i in items):
        message = message or "Low confidence. Please check the names before saving."
    return RecognitionResult(items=items, message=message)


async def recognise_food(image_bytes: bytes, provider: VisionProvider) -> RecognitionResult:
    media_type = detect_media_type(image_bytes)
    raw = await provider.describe(image_bytes, media_type)
    return parse_model_reply(raw)
