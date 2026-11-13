def test_login_required(client):
    r = client.get("/water/forecast", headers={"Authorization": ""})
    assert r.status_code == 401 and "Sign in" in r.json()["detail"]["message"]


def test_wrong_password_message(client):
    r = client.post("/auth/login", json={"email": "demo@livebetter.mu", "password": "nope"})
    assert r.status_code == 401 and r.json()["detail"]["message"] == "Email or password is not correct."


def test_summary_and_insights(client):
    assert client.get("/water/summary").json()["module"] == "water"
    assert client.get("/water/insights").json()["recommendations"]


def test_real_bill_replaces_placeholders_and_overlap_is_refused(client):
    ok = client.post("/water/bills", json={"start": "2026-10-13", "end": "2026-11-12", "m3": 19, "start_reading": 1452, "end_reading": 1471})
    assert ok.status_code == 200
    assert all(b["source"] != "placeholder" for b in client.get("/water/bills").json())
    dup = client.post("/water/bills", json={"start": "2026-10-20", "end": "2026-11-12", "m3": 5})
    assert dup.status_code == 409 and "overlaps" in dup.json()["detail"]["message"]


def test_bill_checks(client):
    r = client.post("/water/bills", json={"start": "2026-10-13", "end": "2026-10-01", "m3": 20})
    assert r.status_code == 422 and "must be after its start date" in r.text
    r = client.post("/water/bills", json={"start": "2026-10-13", "end": "2026-11-12", "m3": 30, "start_reading": 100, "end_reading": 110})
    assert r.status_code == 422 and "Check the numbers" in r.text


def test_reading_checks(client):
    ok = client.post("/water/readings", json={"date": "2026-11-03", "index_m3": 1460})
    assert ok.status_code == 200 and ok.json()["forecast"]["confidence"] == "medium"
    back = client.post("/water/readings", json={"date": "2026-11-10", "index_m3": 1455})
    assert back.status_code == 422 and "backwards" in back.json()["detail"]["message"]
    early = client.post("/water/readings", json={"date": "2026-10-01", "index_m3": 1500})
    assert early.status_code == 422


def test_action_select_complete_is_idempotent(client):
    a = client.post("/water/actions", json={"action": "fix_dripping_tap", "params": {}}).json()
    first = client.post(f"/water/actions/{a['id']}/complete").json()
    again = client.post(f"/water/actions/{a['id']}/complete").json()
    assert first["status"] == again["status"] == "completed"
    assert [x["event"] for x in client.get("/water/activity").json()].count("action_completed") == 1


def test_bad_action_params_give_422(client):
    r = client.post("/water/scenarios", json={"action": "shorter_showers", "params": {"minutes_less": 50}})
    assert r.status_code == 422 and "between" in r.json()["detail"]["message"]
    r = client.post("/water/scenarios", json={"action": "teleport", "params": {}})
    assert r.status_code == 400


def test_profile_validation(client):
    assert client.put("/water/profile", json={"region": "Moon"}).status_code == 422
    assert client.put("/water/profile", json={"members": 3}).json()["members"] == 3
