import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from food_recognition import router as router_mod  # noqa: E402
from food_recognition.service import ImageRejected, detect_media_type, parse_model_reply  # noqa: E402

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"0" * 100


class FakeProvider:
    def __init__(self, reply: str = "", fail: bool = False):
        self.reply, self.fail = reply, fail

    async def describe(self, image_bytes, media_type):
        if self.fail:
            raise RuntimeError("provider down")
        return self.reply


def make_client(provider):
    app = FastAPI()
    app.include_router(router_mod.router)
    app.dependency_overrides[router_mod.get_provider] = lambda: provider
    app.dependency_overrides[router_mod.get_user_context] = lambda: None
    return TestClient(app)


def test_detects_supported_formats():
    assert detect_media_type(JPEG) == "image/jpeg"
    assert detect_media_type(PNG) == "image/png"
    assert detect_media_type(WEBP) == "image/webp"


def test_rejects_unsupported_and_oversized():
    with pytest.raises(ImageRejected):
        detect_media_type(b"GIF89a" + b"0" * 10)
    with pytest.raises(ImageRejected):
        detect_media_type(JPEG + b"0" * (5 * 1024 * 1024))


def test_parses_valid_reply_and_flags_low_confidence():
    reply = json.dumps({"items": [
        {"name": "carrot", "category": "fresh", "confidence": 0.9, "label_text": []},
        {"name": "tin", "category": "packaged", "confidence": 0.3, "label_text": ["PEAS"]},
    ], "message": ""})
    result = parse_model_reply(reply)
    assert [i.name for i in result.items] == ["carrot", "tin"]
    assert result.items[0].low_confidence is False
    assert result.items[1].low_confidence is True
    assert result.needs_confirmation is True


def test_malformed_reply_falls_back_to_manual_entry():
    result = parse_model_reply("sorry, I cannot do that")
    assert result.items == []
    assert "manually" in result.message


def test_invalid_category_falls_back_instead_of_crashing():
    reply = json.dumps({"items": [{"name": "x", "category": "weird", "confidence": 0.9}]})
    assert parse_model_reply(reply).items == []


def test_endpoint_returns_items():
    reply = json.dumps({"items": [{"name": "rice", "category": "packaged",
                                   "confidence": 0.95, "label_text": ["BASMATI"]}]})
    client = make_client(FakeProvider(reply))
    resp = client.post("/food/recognize", files={"image": ("p.jpg", JPEG, "image/jpeg")})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["name"] == "rice"


def test_endpoint_rejects_bad_image():
    client = make_client(FakeProvider("{}"))
    resp = client.post("/food/recognize", files={"image": ("a.gif", b"GIF89a00", "image/gif")})
    assert resp.status_code == 422


def test_endpoint_reports_provider_outage_as_503():
    client = make_client(FakeProvider(fail=True))
    resp = client.post("/food/recognize", files={"image": ("p.jpg", JPEG, "image/jpeg")})
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "vision_unavailable"
