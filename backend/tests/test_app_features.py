"""Features behind the 14 Nov app screens: habits, explainable forecast, bills from the team database,
activity sections, food scan helpers. Local mode, no keys."""
import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    for k in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from core import config, identity, localdb
    config.get_settings.cache_clear()
    monkeypatch.setattr(localdb, "ROOT", str(tmp_path))
    identity._LOCAL_DBS.clear()
    import app as app_module
    importlib.reload(app_module)
    c = TestClient(app_module.app)
    c.headers["Authorization"] = "Bearer " + c.post("/auth/login", json={"email": "demo@livebetter.mu",
                                                                          "password": "demo1234"}).json()["token"]
    c.post("/households/onboarding", json={"name": "Home", "members": 3, "home_type": "House", "monthly_target": 9000})
    yield c
    config.get_settings.cache_clear()


def test_habits_round_trip_and_unlock(client):
    w = client.get("/habits/water").json()
    assert [q["id"] for q in w["questions"]][:2] == ["W1_shower_minutes", "W2_flushes_per_person"]
    assert w["answers"] == {}
    out = client.put("/habits/water", json={"W1_shower_minutes": "11_20", "W4_outdoor_use": "weekly"}).json()
    assert out["answers"]["W1_shower_minutes"] == "11_20"
    assert client.put("/habits/water", json={"W1_shower_minutes": "forever"}).status_code == 422
    e = client.put("/habits/electricity", json={"E1": ["air_conditioner", "kettle", "nonsense"], "E2": "4_8",
                                               "E5": "increase", "expected_change_pct": 10}).json()
    assert e["answers"]["E1"] == ["air_conditioner", "kettle"] and e["answers"]["E2"] == "4_8"
    assert client.get("/electricity/assessment").json()["expected_change_pct"] == 10
    assert client.put("/habits/electricity", json={"E3": "nuclear"}).status_code == 422


def test_explain_forecast(client):
    none = client.get("/utilities/explain", params={"category": "water"}).json()
    assert none["available"] is False and none["factors"] == []
    client.post("/bills", json={"kind": "water", "period_start": "2026-08-13", "period_end": "2026-09-13", "units": 22})
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 24})
    x = client.get("/utilities/explain", params={"category": "water"}).json()
    assert x["available"] and x["summary_source"] == "template" and "Rs" in x["headline"]
    labels = [f["label"] for f in x["factors"]]
    assert {"Expected use", "Estimated bill", "Based on"} <= set(labels)
    assert x["to_improve"]
    assert client.get("/utilities/explain", params={"category": "gas"}).status_code == 422


def test_bills_from_team_database_are_used(client):
    """Rows the database owner seeded straight into utility_bills appear in the module and its forecast."""
    from core import identity
    db = identity.local_db()
    h = client.get("/households/me").json()["household"]
    for s, e, u in (("2026-07-01", "2026-08-01", 120), ("2026-08-01", "2026-09-01", 130)):
        db.table("utility_bills").insert({"household_id": h["id"], "kind": "electricity", "period_start": s,
                                          "period_end": e, "units": u, "amount": None, "tariff_code": "CEB 140"}).execute()
    bills = [b for b in client.get("/bills").json() if b["kind"] == "electricity"]
    assert len(bills) == 2 and bills[0]["units"] == 120
    assert client.get("/utilities/forecast", params={"category": "electricity"}).json()["value"] is not None
    client.post("/bills", json={"kind": "electricity", "period_start": "2026-09-01", "period_end": "2026-10-01", "units": 125})
    assert len([b for b in client.get("/bills").json() if b["kind"] == "electricity"]) == 3       # no duplicates
    assert len(db.rows("utility_bills")) == 3


def test_activity_sections_and_food_helpers(client):
    client.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 18})
    client.post("/household/coach", json={"message": "How can I spend less?"})
    cats = {a["category"] for a in client.get("/activity").json()}
    assert {"water", "ai"} <= cats
    d = client.post("/food/describe", json={"name": "Tomato", "category": "fresh"}).json()
    assert d["source"] == "template" and "tomato" in d["description"]
    assert client.post("/recipes/generate", json={"ingredients": ["tomato"]}).status_code == 503   # needs Gemini
    r = client.post("/bills/parse", data={"kind": "water"}, files={"image": ("b.jpg", b"\xff\xd8\xff" + b"0" * 100, "image/jpeg")})
    assert r.status_code in (422, 503)
