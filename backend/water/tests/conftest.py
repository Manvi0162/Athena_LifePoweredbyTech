import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))   # the backend folder
DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "demo_water.json")


@pytest.fixture()
def state():
    with open(DEMO) as fh:
        return json.load(fh)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from water import app, auth, store
    monkeypatch.setattr(store, "PATH", str(tmp_path / "water_state.json"))
    c = TestClient(app.app)
    t = c.post("/auth/login", json={"email": auth.EMAIL, "password": auth.PASSWORD}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {t}"})
    return c
