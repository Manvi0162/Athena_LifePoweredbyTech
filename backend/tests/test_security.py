"""Surprise card "Misuse": someone with the owner's unlocked phone (a child, a housemate, a controlling partner)
tries to wipe the household's records, delete bills or switch security off. These tests demonstrate the safeguards.
Local mode, no keys needed."""
import importlib
import sys
import time
from pathlib import Path

import pyotp
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
PATTERN = [1, 5, 9, 6, 3]
WRONG = [1, 2, 3, 4]


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    for k in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "GEMINI_API_KEY", "MFA_ENCRYPTION_KEY"):
        monkeypatch.delenv(k, raising=False)
    from core import config, identity, localdb
    config.get_settings.cache_clear()
    monkeypatch.setattr(localdb, "ROOT", str(tmp_path))
    identity._LOCAL_DBS.clear()
    identity._LOGIN_FAILS.clear()
    import app as app_module
    importlib.reload(app_module)
    yield TestClient(app_module.app)
    config.get_settings.cache_clear()


def register(c, email="owner@example.mu", password="owner-pass-1"):
    r = c.post("/auth/signup", json={"email": email, "password": password, "name": "Owner"})
    assert r.status_code == 200, r.text
    c.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return r.json()


def setup_household(c):
    assert c.put("/security/pattern", json={"pattern": PATTERN, "password": "owner-pass-1"}).status_code == 200
    r = c.post("/households/onboarding", json={"name": "Home", "members": 3, "home_type": "House",
                                               "monthly_target": 12000, "main_goal": "reduce_expenses"})
    assert r.status_code == 200, r.text
    c.post("/bills", json={"kind": "water", "period_start": "2026-09-13", "period_end": "2026-10-13", "units": 18})


def permit(c, action, pattern=PATTERN):
    return c.post("/security/pattern/verify", json={"pattern": pattern, "action": action})


def test_signup_login_and_wrong_password_lockout(app_client):
    c = app_client
    out = register(c)
    assert out["user"]["email"] == "owner@example.mu" and out["token"].startswith("lb1.")
    assert c.post("/auth/signup", json={"email": "owner@example.mu", "password": "another-1"}).status_code == 409
    assert c.post("/auth/signup", json={"email": "x@y.mu", "password": "short"}).status_code == 422
    assert c.get("/auth/me").json()["user"]["name"] == "Owner"
    fresh = TestClient(c.app)
    assert fresh.post("/auth/login", json={"email": "owner@example.mu", "password": "owner-pass-1"}).status_code == 200
    codes = [fresh.post("/auth/login", json={"email": "owner@example.mu", "password": "bad"}).status_code
             for _ in range(6)]
    assert codes == [401] * 5 + [423]                                              # 5 wrong -> locked 5 min
    assert fresh.post("/auth/login", json={"email": "owner@example.mu", "password": "owner-pass-1"}).status_code == 423
    assert TestClient(c.app).get("/auth/me", headers={"Authorization": "Bearer lb1.u-fake.abc"}).status_code == 401


def test_pattern_needs_password_and_valid_shape(app_client):
    c = app_client
    register(c)
    assert c.put("/security/pattern", json={"pattern": PATTERN}).status_code == 401              # no password
    assert c.put("/security/pattern", json={"pattern": PATTERN, "password": "nope"}).status_code == 401
    assert c.put("/security/pattern", json={"pattern": [1, 2], "password": "owner-pass-1"}).status_code == 422
    assert c.put("/security/pattern", json={"pattern": PATTERN, "password": "owner-pass-1"}).json()["pattern_set"]


def test_misuse_reset_is_blocked_then_owner_can_undo(app_client):
    """The demo: a child taps 'Reset account'. Without the pattern nothing happens; wrong patterns lock it;
    the owner sees the attempts; even the owner's own reset can be undone for 24 hours."""
    c = app_client
    register(c)
    setup_household(c)
    assert len(c.get("/bills").json()) == 1
    r = c.post("/account/reset")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "pattern_required"
    assert len(c.get("/bills").json()) == 1                                         # nothing deleted
    for left in (4, 3, 2, 1):
        r = permit(c, "reset_account", WRONG)
        assert r.status_code == 401 and r.json()["detail"]["details"]["attempts_left"] == left
    assert permit(c, "reset_account", WRONG).status_code == 423                      # 5th wrong: locked
    assert permit(c, "reset_account", PATTERN).status_code == 423                    # even the right one waits
    st = c.get("/security/status").json()
    assert st["alert"] and st["alert"]["count"] >= 6 and "pattern" in st["locks"]
    assert any(a["event_type"].startswith("security.") for a in c.get("/activity").json())

    # owner, after the lock (simulate 5 minutes passing)
    from core import security as S
    from core.identity import RequestContext, local_db
    from core import accounts
    uid = c.get("/auth/me").json()["user"]["id"]
    ctx = RequestContext(uid, local_db(uid), "local", "owner@example.mu")
    sec = S.load(ctx); sec["locks"] = {}; S.save(ctx, sec)
    tok = permit(c, "reset_account").json()["step_up_token"]
    assert c.post("/account/restore", headers={"X-Step-Up": tok}).status_code == 403   # wrong action
    tok = permit(c, "reset_account").json()["step_up_token"]
    out = c.post("/account/reset", headers={"X-Step-Up": tok}).json()
    assert out["ok"] and c.get("/bills").json() == []
    assert c.post("/account/reset", headers={"X-Step-Up": tok}).status_code == 403    # one use only
    assert c.get("/account/reset-status").json()["restorable"] is True
    tok = permit(c, "restore_account").json()["step_up_token"]
    assert c.post("/account/restore", headers={"X-Step-Up": tok}).json()["ok"]
    assert len(c.get("/bills").json()) == 1                                         # evidence is back
    assert c.get("/account/reset-status").json()["restorable"] is False
    assert accounts.local_user(uid)["password_hash"].startswith("pbkdf2$")


def test_delete_bill_and_household_edit_need_pattern(app_client):
    c = app_client
    register(c)
    setup_household(c)
    kind, bid = c.get("/bills").json()[0]["id"].split(":")
    assert c.delete(f"/bills/{kind}/{bid}").status_code == 403
    assert c.delete(f"/water/bills/{bid}").status_code == 403                         # module route guarded too
    body = {"name": "Changed", "members": 9, "home_type": "House", "monthly_target": 1, "main_goal": "reduce_expenses"}
    assert c.post("/households/onboarding", json=body).status_code == 403
    tok = permit(c, "edit_household").json()["step_up_token"]
    assert c.post("/households/onboarding", json=body, headers={"X-Step-Up": tok}).status_code == 200
    tok = permit(c, "delete_bill").json()["step_up_token"]
    assert c.delete(f"/bills/{kind}/{bid}", headers={"X-Step-Up": tok}).status_code == 200
    assert c.get("/bills").json() == []


def test_authenticator_is_optional_and_protects_login(app_client):
    c = app_client
    register(c)
    assert c.get("/security/status").json()["authenticator_on"] is False             # optional: off by default
    setup = c.post("/security/authenticator/setup").json()
    assert setup["qr_png"].startswith("data:image/png;base64,") and setup["otpauth_uri"].startswith("otpauth://totp/")
    totp = pyotp.TOTP(setup["manual_key"])
    assert c.post("/security/authenticator/confirm", json={"code": "000000"}).status_code == 401
    rec = c.post("/security/authenticator/confirm", json={"code": totp.now()}).json()
    assert rec["enabled"] and len(rec["recovery_codes"]) == 8
    from core import accounts
    uid = c.get("/auth/me").json()["user"]["id"]
    stored = accounts.local_user(uid)["security"]["totp"]["secret"]
    assert setup["manual_key"] not in stored                                          # encrypted at rest

    fresh = TestClient(c.app)
    step1 = fresh.post("/auth/login", json={"email": "owner@example.mu", "password": "owner-pass-1"}).json()
    assert step1["mfa_required"] and "token" not in step1                            # password alone is not enough
    assert fresh.post("/auth/mfa", json={"mfa_token": step1["mfa_token"], "code": "123456"}).status_code == 401
    code_next = totp.at(time.time() + 30)                                             # +1 step allowed (clock drift)
    ok = fresh.post("/auth/mfa", json={"mfa_token": step1["mfa_token"], "code": code_next}).json()
    assert ok["token"].startswith("lb1.")
    again = fresh.post("/auth/mfa", json={"mfa_token": step1["mfa_token"], "code": code_next})
    assert again.status_code == 401                                                   # a code works once
    ok2 = fresh.post("/auth/mfa", json={"mfa_token": step1["mfa_token"], "recovery_code": rec["recovery_codes"][0]})
    assert ok2.status_code == 200
    assert fresh.post("/auth/mfa", json={"mfa_token": step1["mfa_token"],
                                         "recovery_code": rec["recovery_codes"][0]}).status_code == 401

    # switching it off needs the pattern AND a code
    c.put("/security/pattern", json={"pattern": PATTERN, "recovery_code": rec["recovery_codes"][1]})
    assert c.get("/security/status").json()["pattern_set"]
    assert c.post("/security/authenticator/disable", json={"recovery_code": rec["recovery_codes"][2]}).status_code == 403
    tok = permit(c, "security_off").json()["step_up_token"]
    assert c.post("/security/authenticator/disable", headers={"X-Step-Up": tok}, json={}).status_code == 401
    tok = permit(c, "security_off").json()["step_up_token"]
    off = c.post("/security/authenticator/disable", headers={"X-Step-Up": tok},
                 json={"recovery_code": rec["recovery_codes"][2]}).json()
    assert off["authenticator_on"] is False
    assert "token" in TestClient(c.app).post("/auth/login", json={"email": "owner@example.mu",
                                                                  "password": "owner-pass-1"}).json()


def test_sample_never_overwrites_real_data(app_client):
    c = app_client
    register(c)
    setup_household(c)
    assert c.post("/demo/sample").status_code == 409
