import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))   # the backend folder
DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


@pytest.fixture()
def sample():
    return _load("sample_water.json")


@pytest.fixture()
def empty():
    s = _load("empty_water.json")
    s["today"] = "2026-11-13"
    return s


@pytest.fixture()
def one_bill(empty):
    s = copy.deepcopy(empty)
    s["household"]["members"] = 4
    s["profile"]["sewer"] = False
    s["bills"] = [{"id": "b1", "start": "2026-09-13", "end": "2026-10-13", "m3": 18.0, "amount_rs": None,
                   "end_reading": 1450.0, "source": "confirmed"}]
    return s


ALL_ANSWERS = {"W1_shower_minutes": "5_10", "W2_flushes_per_person": "4_6", "W3_laundry_loads_per_week": "3_5",
               "W4_outdoor_use": "weekly", "W5_expected_change": "no"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from water import app, auth, store
    monkeypatch.setattr(store, "PATH", str(tmp_path / "water_state.json"))
    c = TestClient(app.app)
    t = c.post("/auth/login", json={"email": auth.EMAIL, "password": auth.PASSWORD}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {t}"})
    c.put("/water/profile", json={"today": "2026-11-13"})
    return c
