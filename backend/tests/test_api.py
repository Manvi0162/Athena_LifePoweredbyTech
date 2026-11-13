def test_login_required(client):
    r = client.get("/utilities/forecast", headers={"Authorization": ""})
    assert r.status_code == 401 and "Sign in" in r.json()["detail"]["message"]


def test_wrong_password_message(client):
    r = client.post("/auth/login", json={"email": "demo@livebetter.mu", "password": "nope"})
    assert r.status_code == 401 and r.json()["detail"]["message"] == "Email or password is not correct."


def test_forecast_and_insights(client):
    f = client.get("/utilities/forecast").json()
    assert f["water"]["status"] == "ok" and f["electricity"]["status"] == "ok"
    assert client.get("/household/insights").json()["recommendations"]


def test_action_select_complete_is_idempotent(client):
    a = client.post("/actions", json={"action": "standby_off", "params": {}}).json()
    first = client.post(f"/actions/{a['id']}/complete").json()
    again = client.post(f"/actions/{a['id']}/complete").json()
    assert first["status"] == "completed" and again["status"] == "completed"
    events = [x["event"] for x in client.get("/activity").json()]
    assert events.count("action_completed") == 1


def test_bill_validation_errors_are_specific(client):
    r = client.post("/bills", json={"utility": "water", "start": "2026-10-13", "end": "2026-10-01", "units": 20})
    assert r.status_code == 422 and "must be after its start date" in r.text
    ok = client.post("/bills", json={"utility": "water", "start": "2026-10-13", "end": "2026-11-12", "units": 19})
    assert ok.status_code == 200 and all(b.get("source") != "placeholder" for b in ok.json()["bills"] if b["utility"] == "water")
    dup = client.post("/bills", json={"utility": "water", "start": "2026-10-20", "end": "2026-11-12", "units": 5})
    assert dup.status_code == 409 and "overlaps" in dup.json()["detail"]["message"]


def test_profile_tariff_validation(client):
    r = client.put("/household", json={"ceb_tariff": "999"})
    assert r.status_code == 422 and "110, 120 or 140" in r.text
