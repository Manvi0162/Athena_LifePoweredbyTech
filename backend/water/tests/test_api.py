"""Demo storyline from the spec, through the API."""


def test_login_required(client):
    r = client.get("/water/forecast", headers={"Authorization": ""})
    assert r.status_code == 401 and "log in" in r.json()["detail"]["message"]


def test_demo_storyline(client):
    # register -> empty water forecast
    client.put("/water/household", json={"members": 4, "home_type": "house", "occupancy": "variable", "main_goal": "all"})
    f = client.get("/water/forecast").json()
    assert f["status"] == "insufficient_data" and f["estimated_units"] is None
    # upload first (confirmed) bill -> preliminary estimate + saved snapshot
    r = client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 18, "amount_rs": 148,
                                          "start_reading": 1432, "end_reading": 1450})
    assert r.status_code == 200 and r.json()["forecast"]["status"] == "preliminary"
    assert r.json()["tariff_check"]["ok"]                    # 10x6 + 8x8 + meter 10 + postal 14 = Rs 148
    # optional water questions -> completeness up
    a = client.put("/water/assessment", json={"W1_shower_minutes": "5_10", "W4_outdoor_use": "never"}).json()
    assert a["version"] == 1 and not a["complete"]
    # simulate savings
    s = client.post("/water/scenarios", json={"scenario": "shorter_showers", "params": {"minutes_less": 2}}).json()
    assert s["status"] == "ok" and s["difference"]["rs"] < 0
    # explain limitations: summary carries status, completeness, reliability
    summ = client.get("/water/summary").json()
    assert summ["status"] == "preliminary" and summ["data_completeness"]["pct"] < 100
    events = [e["event"] for e in client.get("/water/activity").json()]
    for e in ("household_answered", "bill_confirmed", "forecast_issued", "assessment_answered", "scenario_run"):
        assert e in events


def test_next_bill_is_checked_against_saved_forecast(client):
    client.post("/water/bills", json={"start": "2026-08-13", "end": "2026-09-13", "m3": 18})
    client.put("/water/profile", json={"today": "2026-10-14"})
    r = client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 21}).json()
    assert r["forecast_check"] and r["forecast_check"]["actual_m3"] == 21
    checks = client.get("/water/checks").json()
    assert checks["reliability"]["checked_forecasts"] == 1 and checks["reliability"]["backtests"] == 1


def test_bill_validation(client):
    r = client.post("/water/bills", json={"start": "2026-10-13", "end": "2026-10-01", "m3": 20})
    assert r.status_code == 422 and "must be after its start date" in r.text
    r = client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 30, "start_reading": 100, "end_reading": 110})
    assert r.status_code == 422 and "Check the numbers" in r.text
    client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 20})
    dup = client.post("/water/bills", json={"start": "2026-09-20", "end": "2026-10-20", "m3": 5})
    assert dup.status_code == 409 and "overlap it" in dup.json()["detail"]["message"]


def test_tariff_mismatch_is_flagged(client):
    r = client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 24, "amount_rs": 400}).json()
    assert r["tariff_check"]["ok"] is False and r["tariff_check"]["tariff_calculated_rs"] == 232.0


def test_readings_rules(client):
    client.post("/water/bills", json={"start": "2026-09-13", "end": "2026-10-13", "m3": 18, "start_reading": 1432, "end_reading": 1450})
    assert client.get("/water/forecast/current").json()["status"] == "needs_readings"
    ok = client.post("/water/readings", json={"date": "2026-11-03", "index_m3": 1458})
    assert ok.status_code == 200 and ok.json()["current_cycle"]["status"] == "measured_projection"
    back = client.post("/water/readings", json={"date": "2026-11-10", "index_m3": 1455})
    assert back.status_code == 422 and "only goes up" in back.json()["detail"]["message"]


def test_goal_needs_data_and_complete_is_idempotent(client):
    client.put("/water/household", json={"members": 4})
    r = client.post("/water/actions", json={"scenario": "shorter_showers", "params": {}})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "needs_input"
    a = client.post("/water/actions", json={"scenario": "fix_dripping_tap", "params": {}}).json()
    client.post(f"/water/actions/{a['id']}/complete")
    client.post(f"/water/actions/{a['id']}/complete")
    assert [e["event"] for e in client.get("/water/activity").json()].count("action_completed") == 1


def test_validation_messages(client):
    assert client.put("/water/household", json={"members": 0}).status_code == 422
    assert client.put("/water/assessment", json={"W1_shower_minutes": "forever"}).status_code == 422
    assert client.put("/water/profile", json={"region": "Moon"}).status_code == 422
    r = client.post("/water/scenarios", json={"scenario": "teleport"})
    assert r.status_code == 400


def test_sample_household_for_rehearsal(client):
    client.post("/water/demo/reset?sample=true")
    s = client.get("/water/summary").json()
    assert s["status"] == "better_supported" and s["forecast_vs_actual"]
    assert client.get("/water/seasons").json()["dearest"] in {"Jan", "Feb", "Mar"}
