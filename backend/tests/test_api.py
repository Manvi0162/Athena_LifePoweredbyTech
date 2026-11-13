"""API tests. Table reads use an in-memory fake; RPC calls run her real SQL
functions in a local PostgreSQL when one is available (see conftest)."""

import hashlib
import json
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module  # noqa: E402
from core import auth, llm  # noqa: E402
from receipts import router as receipts_router  # noqa: E402
from recipes import router as recipes_router  # noqa: E402

HOUSEHOLD = {"id": "fe951ebe-54ab-42ec-9868-07ee674a90fa", "name": "LiveBetter Demo Household",
             "members": 4, "currency": "MUR"}
USER = "71d8eafb-0035-412b-90ac-ad8a7f44f14d"
JPEG = b"\xff\xd8\xff\xe0" + b"receipt-photo" * 10


# ---------------- in-memory fake for table reads ----------------
class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)

    def select(self, *_):
        return self

    def eq(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) == val]
        return self

    def gt(self, col, val):
        self.rows = [r for r in self.rows if r.get(col) is not None and r[col] > val]
        return self

    def order(self, col, desc=False):
        self.rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def execute(self):
        return type("Resp", (), {"data": self.rows})()


class FakeDB:
    def __init__(self, tables, rpc_handler=None):
        self.tables, self.rpc_handler, self.rpc_calls = tables, rpc_handler, []

    def table(self, name):
        return FakeQuery(self.tables.get(name, []))

    def rpc(self, name, params):
        self.rpc_calls.append((name, params))
        db = self

        class Call:
            def execute(self_inner):
                return type("Resp", (), {"data": db.rpc_handler(name, params)})()
        return Call()


def recipe(rid, name, status, ings):
    return {"id": rid, "name": name, "verification_status": status, "youtube_url": None,
            "lb_recipe_ingredients": [{"ingredient_name": n, "quantity": q, "unit": u,
                                       "optional": o} for n, q, u, o in ings]}


RECIPES = [
    recipe("r-fried", "Chicken and Carrot Fried Rice", "pending",
           [("rice", 0.5, "kg", False), ("carrots", 0.3, "kg", False),
            ("eggs", 4, "piece", False), ("cooking oil", 30, "ml", False), ("salt", 5, "g", True),
            ("water", 1, "l", False)]),
    recipe("r-dholl", "Dholl puri", "verified", [("flour", 500, "g", False), ("split peas", 200, "g", False)]),
]
PANTRY = [
    {"household_id": HOUSEHOLD["id"], "ingredient_name": "rice", "quantity": 5.5, "unit": "kg", "available": True},
    {"household_id": HOUSEHOLD["id"], "ingredient_name": "eggs", "quantity": 14, "unit": "piece", "available": True},
    {"household_id": HOUSEHOLD["id"], "ingredient_name": "carrots", "quantity": 2.7, "unit": "kg", "available": True},
]


def make_client(db):
    app_module.app.dependency_overrides[auth.get_household_context] = (
        lambda: auth.HouseholdContext(user_id=USER, db=db, household=HOUSEHOLD))
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app_module.app.dependency_overrides.clear()


# ---------------- auth ----------------
def test_health_needs_no_login():
    assert TestClient(app_module.app).get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/pantry", "/household", "/recipes"])
def test_endpoints_require_login(path):
    resp = TestClient(app_module.app).get(path)
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "unauthorized"


def test_food_recognize_requires_login():
    resp = TestClient(app_module.app).post("/food/recognize", files={"image": ("p.jpg", JPEG, "image/jpeg")})
    assert resp.status_code == 401


def test_settings_refuse_secret_key(monkeypatch):
    from core.config import Settings
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_secret_abc")
    with pytest.raises(RuntimeError):
        Settings()


# ---------------- photo -> recipes ----------------
def test_search_finds_recipes_using_photo_ingredient():
    client = make_client(FakeDB({"lb_recipes": RECIPES, "pantry_items": PANTRY}))
    body = client.post("/recipes/search", json={"ingredients": ["Carrots"]}).json()
    assert body["searched"] == 2
    [match] = body["matches"]
    assert match["name"] == "Chicken and Carrot Fried Rice"
    assert match["uses_from_photo"] == ["carrots"]
    assert match["already_in_pantry"] == ["rice", "eggs"]
    assert match["still_to_buy"] == ["cooking oil"]  # salt optional, water never "to buy"
    assert match["youtube"]["type"] == "search results"


def test_search_rejects_empty_list():
    client = make_client(FakeDB({"lb_recipes": RECIPES, "pantry_items": PANTRY}))
    assert client.post("/recipes/search", json={"ingredients": []}).status_code == 422


# ---------------- recommend ----------------
def test_recommend_uses_ai_draft_when_no_verified_recipe_is_cookable(monkeypatch):
    draft = {"name": "Egg rice", "ingredients": [{"ingredient_name": "rice", "quantity": 0.2, "unit": "kg"}],
             "instructions": ["cook"]}
    monkeypatch.setattr(recipes_router, "generate_recipe", lambda *a, **k: draft)
    client = make_client(FakeDB({"lb_recipes": RECIPES, "pantry_items": PANTRY}))
    body = client.post("/recipes/recommend", json={}).json()
    assert body["source"] == "ai_generated" and body["recipe"]["name"] == "Egg rice"
    assert body["cook_now"] is True


def test_recommend_prefers_cookable_verified_recipe(monkeypatch):
    monkeypatch.setattr(recipes_router, "generate_recipe",
                        lambda *a, **k: pytest.fail("AI should not be called"))
    pantry = PANTRY + [
        {"household_id": HOUSEHOLD["id"], "ingredient_name": "flour", "quantity": 1, "unit": "kg", "available": True},
        {"household_id": HOUSEHOLD["id"], "ingredient_name": "split peas", "quantity": 500, "unit": "g", "available": True}]
    client = make_client(FakeDB({"lb_recipes": RECIPES, "pantry_items": pantry}))
    body = client.post("/recipes/recommend", json={}).json()
    assert body["source"] == "verified_database" and body["recipe"]["name"] == "Dholl puri"


def test_recommend_reports_ai_outage_as_503(monkeypatch):
    def down(*a, **k):
        raise llm.LLMUnavailable("all busy")
    monkeypatch.setattr(recipes_router, "generate_recipe", down)
    client = make_client(FakeDB({"lb_recipes": RECIPES, "pantry_items": PANTRY}))
    assert client.post("/recipes/recommend", json={}).status_code == 503


# ---------------- receipts ----------------
def winners_reply(monkeypatch, items):
    replies = iter(["WINNERS FOREST SIDE ...", json.dumps({
        "store_name": "WINNERS FOREST SIDE", "receipt_date": "2026-10-01", "receipt_total": 1207.10,
        "items": items, "uncertain_parts": []})])
    monkeypatch.setattr(receipts_router, "gemini_generate", lambda *a, **k: next(replies))


def line(name, norm, qty, unit, price, category):
    return {"original_name": name, "normalized_name": norm, "quantity": qty, "unit": unit,
            "line_total": price, "category": category}


def test_parse_receipt_excludes_non_food_and_totals_food_only(monkeypatch):
    winners_reply(monkeypatch, [
        line("LUCOZADE ENERGY ORAN", "Lucozade Energy Orange", 1, "piece", 74.95, "food"),
        line("EVEREADY H DUTY AAA", "Eveready AAA Batteries", 1, "piece", 49.60, "non_food"),
        line("COLG DENT 75ML CHARC", "Colgate Charcoal Toothpaste", 2, "piece", 109.00, "non_food"),
        line("B.CHERI BLACK LABEL", "Bois Cheri Black Label Tea", 2, "piece", 69.00, "food"),
        line("USB CHARGING", "USB Charging Cable", 1, "piece", 50.00, "non_food"),
        line("MYSTERY ITEM", "Mystery", 1, "piece", 10.00, None),  # unlabelled: kept for review
    ])
    client = make_client(FakeDB({}))
    body = client.post("/receipts/parse", files={"image": ("r.jpg", JPEG, "image/jpeg")}).json()
    assert body["source_identifier"] == hashlib.sha256(JPEG).hexdigest()
    assert [i["normalized_name"] for i in body["items"]] == [
        "lucozade energy orange", "bois cheri black label tea", "mystery"]
    assert body["excluded_non_food"] == ["EVEREADY H DUTY AAA", "COLG DENT 75ML CHARC", "USB CHARGING"]
    assert body["total"] == 153.95            # 74.95 + 69.00 + 10.00
    assert body["receipt_total"] == 1207.10   # whole receipt, display only
    assert body["needs_confirmation"] is True


def test_parse_receipt_still_rejects_unsupported_units(monkeypatch):
    winners_reply(monkeypatch, [line("RICE 2KG", "Rice", 2, "kg", 120, "food"),
                                line("TEA BOX", "Tea", 1, "unknown", 40, "food")])
    body = make_client(FakeDB({})).post(
        "/receipts/parse", files={"image": ("r.jpg", JPEG, "image/jpeg")}).json()
    assert [i["normalized_name"] for i in body["items"]] == ["rice"]
    assert body["rejected_items"][0]["reason"] == "unsupported unit"


def test_confirm_never_sends_non_food_to_database():
    db = FakeDB({}, lambda name, params: "receipt-1")
    client = make_client(db)
    resp = client.post("/receipts/confirm", json={
        "source_identifier": "sha", "total": 124.95, "items": [
            {"normalized_name": "rice", "quantity": 2, "unit": "kg", "line_total": 75.95, "category": "food"},
            {"normalized_name": "batteries", "quantity": 1, "unit": "piece", "line_total": 49.0,
             "category": "non_food"}]})
    assert resp.status_code == 200
    _, params = db.rpc_calls[0]
    assert [i["normalized_name"] for i in params["p_items"]] == ["rice"]
    assert "category" not in params["p_items"][0]
    assert params["p_total"] == 75.95  # recomputed because a line was dropped


def test_confirm_with_only_non_food_is_refused():
    db = FakeDB({}, lambda name, params: pytest.fail("must not reach the database"))
    resp = make_client(db).post("/receipts/confirm", json={
        "source_identifier": "sha", "total": 49, "items": [
            {"normalized_name": "batteries", "quantity": 1, "unit": "piece", "line_total": 49,
             "category": "non_food"}]})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "no_food_items"


def test_parse_receipt_rejects_non_image():
    client = make_client(FakeDB({}))
    resp = client.post("/receipts/parse", files={"image": ("r.gif", b"GIF89a....", "image/gif")})
    assert resp.status_code == 422


def test_parse_receipt_ai_outage_is_503(monkeypatch):
    def down(*a, **k):
        raise llm.LLMUnavailable("busy")
    monkeypatch.setattr(receipts_router, "gemini_generate", down)
    client = make_client(FakeDB({}))
    resp = client.post("/receipts/parse", files={"image": ("r.jpg", JPEG, "image/jpeg")})
    assert resp.status_code == 503


# ---------------- cooking error mapping ----------------
@pytest.mark.parametrize("message,code,status", [
    ("Insufficient ingredient: eggs (need 4 piece, have 2 piece)", "P0001", 409),
    ("Operation ID already used", "P0001", 409),
    ("Recipe not accessible", "P0001", 404),
    ("Unauthorized household", "P0001", 403),
])
def test_cook_maps_database_errors(message, code, status):
    def handler(name, params):
        raise APIError({"message": message, "code": code})
    client = make_client(FakeDB({}, handler))
    resp = client.post("/recipes/r-fried/cook", json={"operation_id": str(uuid.uuid4())})
    assert resp.status_code == status
    assert resp.json()["detail"]["message"] == message


def test_cook_requires_operation_id():
    client = make_client(FakeDB({}, lambda *a: {}))
    assert client.post("/recipes/r-fried/cook", json={}).status_code == 422


# ---------------- Gemini fallback (same rules as the notebook) ----------------
def run_llm(statuses):
    calls = []

    def handler(request):
        model = request.url.path.split("/models/")[1].split(":")[0]
        calls.append(model)
        status = statuses[model].pop(0)
        if status == "timeout":
            raise httpx.ReadTimeout("slow", request=request)
        body = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}
        return httpx.Response(status, json=body if status == 200 else {"error": {}})

    result = llm.gemini_generate(["hi"], models=list(statuses), api_key="k",
                                 transport=httpx.MockTransport(handler), retry_delay=0)
    return result, calls


def test_llm_busy_model_retried_once_then_next():
    assert run_llm({"a": [503, 503], "b": [200]}) == ('{"ok": true}', ["a", "a", "b"])


def test_llm_timeout_and_missing_model_skip_to_next():
    assert run_llm({"a": ["timeout"], "b": [404], "c": [200]})[1] == ["a", "b", "c"]


def test_llm_bad_key_stops_immediately():
    with pytest.raises(llm.LLMUnavailable):
        run_llm({"a": [403], "b": [200]})
