"""End-to-end: the whole app through one backend (local mode, no keys needed).

Checks that the modules affect each other through the shared household:
onboarding -> water/electricity; bills -> forecasts -> Big Brain; receipt -> pantry -> recipes -> cooking;
water + electricity answers -> cross-module action; every event -> one activity log.
"""
import importlib
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from core import config, identity, localdb
    config.get_settings.cache_clear()
    monkeypatch.setattr(localdb, "ROOT", str(tmp_path))
    identity._LOCAL_DBS.clear()
    import app as app_module
    importlib.reload(app_module)
    c = TestClient(app_module.app)
    token = c.post("/auth/login", json={"email": "demo@livebetter.mu", "password": "demo1234"}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {token}"})
    yield c
    config.get_settings.cache_clear()


PATTERN = [1, 2, 3, 6, 9]


def step_up(c, action):
    """Draw the security pattern for one sensitive action (misuse safeguard) -> X-Step-Up header."""
    if not c.get("/security/status").json()["pattern_set"]:
        assert c.put("/security/pattern", json={"pattern": PATTERN, "password": "demo1234"}).status_code == 200
    r = c.post("/security/pattern/verify", json={"pattern": PATTERN, "action": action})
    assert r.status_code == 200, r.text
    return {"X-Step-Up": r.json()["step_up_token"]}


def onboard(c, **extra):
    body = {"name": "Test home", "members": 4, "home_type": "House", "monthly_target": 15000,
            "electricity_tariff": "140", "main_goal": "reduce_expenses", **extra}
    headers = step_up(c, "edit_household") if c.get("/auth/me").json().get("onboarding_required") is False else {}
    r = c.post("/households/onboarding", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_login_and_onboarding_gate(client):
    assert client.get("/info").json()["mode"] == "local"
    assert client.post("/auth/login", json={"email": "demo@livebetter.mu", "password": "x"}).status_code == 401
    assert client.get("/auth/me").json()["onboarding_required"] is True
    r = client.get("/water/forecast")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "onboarding_required"
    out = onboard(client)
    assert out["household"]["members"] == 4
    assert client.get("/households/me").json()["household"]["name"] == "Test home"
    assert TestClient(client.app).get("/water/forecast").status_code == 401        # no token


def test_household_size_is_shared_with_water_and_electricity(client):
    onboard(client, members=3)
    assert client.get("/water/household").json()["members"] == 3
    assert client.get("/electricity/profile").json()["members"] == 3
    assert client.get("/electricity/profile").json()["ceb_tariff"] == "140"
    onboard(client, members=5)                                                   # edit once, all modules follow
    assert client.get("/water/household").json()["members"] == 5


def test_bills_forecasts_and_big_brain(client):
    onboard(client)
    f = client.get("/utilities/forecast", params={"category": "water"}).json()
    assert f["value"] is None and f["confidence"] == "unavailable"                # no invented forecast
    r = client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13",
                                    "units": 18, "amount": 148, "tariff": "Domestic"})
    assert r.status_code == 200, r.text
    assert r.json()["tariff_check"]["ok"] and r.json()["forecast"]["confidence"] == "limited_history"
    r = client.post("/bills", json={"kind": "electricity", "period_start": "2026-08-28", "period_end": "2026-09-28",
                                    "units": 145, "amount": 998, "tariff": "140"})
    assert r.status_code == 200, r.text
    bills = client.get("/bills").json()
    assert {b["kind"] for b in bills} == {"water", "electricity"}
    e = client.get("/utilities/forecast", params={"category": "electricity"}).json()
    assert e["value"] > 0 and e["unit"] == "kWh"
    ins = client.get("/household/insights").json()
    assert ins["water"] > 0 and ins["electricity"] > 0 and ins["total"] is None
    assert ins["module_status"] == {"food": "insufficient_data", "water": "data_available", "electricity": "data_available"}
    for a in ins["actions"]:                                                    # Big Brain report, section 6
        for k in ("source", "module", "action_id", "title", "priority_score", "estimated_savings_mur", "evidence",
                  "explanation"):
            assert k in a
    scores = [a["priority_score"] for a in ins["actions"]]
    assert scores == sorted(scores, reverse=True)                               # one unified ranking
    assert all(a["explanation_source"] == "template" for a in ins["actions"])   # no Gemini key -> templates


def test_bill_validation_messages_reach_the_app(client):
    onboard(client)
    r = client.post("/bills", json={"kind": "water", "period_start": "2026-10-13", "period_end": "2026-10-01", "units": 5})
    assert r.status_code == 422 and "must be after its start date" in r.json()["detail"]["message"]


def test_receipt_pantry_recipe_cook_once(client):
    onboard(client)
    r = client.post("/receipts/confirm", json={"source_identifier": "manual-1", "total": 238, "items": [
        {"normalized_name": "rice", "quantity": 1, "unit": "kg", "line_total": 95},
        {"normalized_name": "carrot", "quantity": 2, "unit": "piece", "line_total": 28},
        {"normalized_name": "peas", "quantity": 0.5, "unit": "kg", "line_total": 70},
        {"normalized_name": "onion", "quantity": 3, "unit": "piece", "line_total": 45}]})
    assert r.status_code == 200, r.text
    again = client.post("/receipts/confirm", json={"source_identifier": "manual-1", "total": 238, "items": [
        {"normalized_name": "rice", "quantity": 1, "unit": "kg", "line_total": 95}]})
    assert again.json()["receipt_id"] == r.json()["receipt_id"]               # confirmed once
    pantry = {p["ingredient_name"]: p for p in client.get("/pantry").json()["items"]}
    assert pantry["rice"]["quantity"] == 1
    recipes = client.get("/recipes/ranked").json()["recipes"]
    fried = next(x for x in recipes if x["name"] == "Vegetable Fried Rice")
    assert fried["cook_now"] and recipes[0]["cook_now"]
    op = str(uuid.uuid4())
    first = client.post(f"/recipes/{fried['id']}/cook", json={"operation_id": op}).json()
    second = client.post(f"/recipes/{fried['id']}/cook", json={"operation_id": op}).json()
    assert first["status"] == "confirmed" and second["status"] == "already_confirmed"
    pantry = {p["ingredient_name"]: p for p in client.get("/pantry").json()["items"]}
    assert pantry["rice"]["quantity"] == 0.8                                   # deducted once
    ins = client.get("/household/insights").json()
    assert ins["groceries_recorded"] == 238                                    # cooking adds no expense
    events = [a["event_type"] for a in client.get("/activity").json()]
    assert "receipt_confirmed" in events and events.count("recipe_cooked") == 1


def test_manual_pantry_add_and_edit(client):
    onboard(client)
    items = client.post("/pantry", json={"name": "Eggs", "quantity": 6, "unit": "piece"}).json()["items"]
    egg = next(i for i in items if i["ingredient_name"] == "eggs")
    items = client.patch("/pantry", json={"id": egg["id"], "available": False}).json()["items"]
    assert next(i for i in items if i["id"] == egg["id"])["available"] is False
    assert client.post("/pantry", json={"name": "x", "quantity": 1, "unit": "bags"}).status_code == 422


def test_scenarios_from_the_app(client):
    onboard(client)
    r = client.post("/household/scenarios", json={"category": "water", "reduction_percent": 10}).json()
    assert r["status"] == "needs_input"                                         # no bill yet: says so
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 24})
    r = client.post("/household/scenarios", json={"category": "water", "reduction_percent": 10}).json()
    assert r["baseline"] > r["adjusted"] and r["delta"] > 0
    client.post("/bills", json={"kind": "electricity", "period_start": "2026-08-28", "period_end": "2026-09-28", "units": 145})
    r = client.post("/household/scenarios", json={"category": "electricity", "reduction_percent": 10}).json()
    assert r["delta"] > 0 and "CEB" in r["message"]


def test_cross_module_hot_water_action(client):
    onboard(client)
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 24})
    client.post("/bills", json={"kind": "electricity", "period_start": "2026-08-28", "period_end": "2026-09-28", "units": 145})
    client.put("/water/assessment", json={"W1_shower_minutes": "5_10"})
    ids = [a["action_id"] for a in client.get("/household/dashboard").json()["actions"]]
    assert "shorter_showers" in ids and "shorter_showers_hot_water" not in ids
    client.put("/electricity/assessment", json={"E1": ["water_heater"], "E3": "electric"})
    acts = {a["action_id"]: a for a in client.get("/household/dashboard").json()["actions"]}
    cross = acts["shorter_showers_hot_water"]
    assert cross["evidence"]["kwh_saved"] > 0 and cross["estimated_savings_mur"] > acts["shorter_showers"]["estimated_savings_mur"]


def test_gemini_number_check(client, monkeypatch):
    onboard(client)
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 24})
    from big_brain import explain
    from core import config, llm
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config.get_settings.cache_clear()
    explain._CACHE.clear()

    def fake(parts, **_):
        import json
        actions = json.loads(parts[0].split("ACTIONS:\n", 1)[1])
        return json.dumps({"explanations": [{"id": a["id"], "explanation": "You will save Rs 99999 for sure."
                                             if i == 0 else "A clear, useful step for your home."}
                                            for i, a in enumerate(actions)]})
    monkeypatch.setattr(llm, "gemini_generate", fake)
    acts = client.get("/household/dashboard").json()["actions"]
    assert acts[0]["explanation_source"] == "template"                         # invented number rejected
    assert "99999" not in acts[0]["explanation"]
    assert any(a["explanation_source"] == "gemini" for a in acts[1:8])


def test_coach_uses_module_numbers(client):
    onboard(client)
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 24})
    a = client.post("/household/coach", json={"message": "How can I spend less?"}).json()
    assert a["intent"] == "chat" and "What would you like to try" in a["answer"] and not a["changes"]
    w = client.post("/household/coach", json={"message": "What if I use 10% less water?"}).json()
    assert w["intent"] == "what_if" and w["changes"][0]["status"] == "ok" and w["changes"][0]["delta_rs"] <= 0


def test_shared_tables_are_written(client):
    onboard(client)
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 18})
    from core import identity
    db = identity.local_db()
    assert any(b["kind"] == "water" and b["units"] == 18 for b in db.rows("utility_bills"))
    assert any(r["event_type"] == "water.bill_confirmed" for r in db.rows("activity_logs"))
    bill = client.get("/bills").json()[0]
    kind, bid = bill["id"].split(":")
    assert client.delete(f"/bills/{kind}/{bid}").status_code == 403          # no pattern -> refused
    assert client.delete(f"/bills/{kind}/{bid}", headers=step_up(client, "delete_bill")).status_code == 200
    assert not any(b["kind"] == "water" for b in db.rows("utility_bills"))


def test_sample_household(client):
    assert client.post("/demo/sample").json()["ok"]
    d = client.get("/household/dashboard").json()
    assert d["status"] == "success" and d["module_status"]["water"] == "data_available"
    assert d["module_details"]["water"]["status"] == "better_supported"
    ids = [a["action_id"] for a in d["actions"]]
    assert "cook_from_pantry" in ids and "complete_expiry_tracking" not in ids and "shorter_showers_hot_water" not in ids
    assert client.post("/demo/sample").status_code == 409                       # never overwrites real data
    assert client.post("/demo/reset").status_code == 403
    assert client.post("/demo/reset", headers=step_up(client, "reset_account")).json()["ok"]
    assert client.get("/utilities/forecast", params={"category": "water"}).json()["value"] is None


def test_big_brain_v3_from_manvi_notebook(client):
    from big_brain import v3
    a = v3.normalize_savings_period({"estimated_savings_mur": 60, "savings_period": "2026-10-01 to 2026-10-16",
                                     "has_valid_savings": True})
    assert a["normalized_savings_30d_mur"] == 120.0 and a["source_period_days"] == 15
    assert v3.normalize_savings_period({"estimated_savings_mur": 50, "savings_period": "month",
                                        "has_valid_savings": True})["normalized_savings_30d_mur"] == 50.0
    assert v3.normalize_savings_period({"estimated_savings_mur": 5, "savings_period": "week",
                                        "has_valid_savings": True})["normalization_status"] == "not_comparable"
    client.post("/demo/sample")
    d = client.get("/big-brain/dashboard", params={"explain": False}).json()
    assert d["version"] == "3.0" and d["data_sources"]["water"] == "household_records"
    recs = d["dashboard"]["recommendations"]
    assert recs and [r["rank"] for r in recs] == list(range(1, len(recs) + 1))
    assert all(recs[i]["normalized_savings_30d_mur"] >= recs[i + 1]["normalized_savings_30d_mur"]
               for i in range(len(recs) - 1))
    assert {r["module"] for r in recs} == {"water", "electricity"} and d["dashboard"]["summary"]
    ins = client.get("/household/insights", params={"explain": False}).json()
    assert ins["big_brain_summary"] == d["dashboard"]["summary"] and ins["savings_30d"]
