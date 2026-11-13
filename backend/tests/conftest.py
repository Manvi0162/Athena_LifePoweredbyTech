import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def household():
    import json
    with open(os.path.join(os.path.dirname(__file__), "..", "data", "demo_household.json")) as fh:
        return json.load(fh)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from utility_engine import api, store
    monkeypatch.setattr(store, "PATH", str(tmp_path / "household.json"))
    c = TestClient(api.app)
    t = c.post("/auth/login", json={"email": api.EMAIL, "password": api.PASSWORD}).json()["token"]
    c.headers.update({"Authorization": f"Bearer {t}"})
    return c
