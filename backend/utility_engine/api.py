"""FastAPI routes for the water + electricity part (single household account).

Run:  uvicorn utility_engine.api:app --reload --port 8000    (from the backend folder)
Docs: http://localhost:8000/docs
Login: one account. Set LIVEBETTER_EMAIL / LIVEBETTER_PASSWORD (defaults below are for the demo only).
"""
import hashlib
import hmac
import os
import uuid
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from . import actions, advice, store
from .forecast import forecast
from .history import daily_history

app = FastAPI(title="LiveBetter utility engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

EMAIL = os.environ.get("LIVEBETTER_EMAIL", "demo@livebetter.mu")
PASSWORD = os.environ.get("LIVEBETTER_PASSWORD", "demo1234")
SECRET = os.environ.get("LIVEBETTER_SECRET", "change-me")
TOKEN = hmac.new(SECRET.encode(), EMAIL.encode(), hashlib.sha256).hexdigest()


def err(status, code, message, details=None):
    raise HTTPException(status, {"code": code, "message": message, "details": details or {}})


def auth(authorization: str = Header(default="")):
    if os.environ.get("LIVEBETTER_NO_AUTH") == "1":
        return
    if authorization != f"Bearer {TOKEN}":
        err(401, "unauthorised", "Sign in first: POST /auth/login with the household email and password.")


class Login(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(b: Login):
    if b.email.strip().lower() != EMAIL.lower() or not hmac.compare_digest(b.password, PASSWORD):
        err(401, "wrong_details", "Email or password is not correct.")
    return {"token": TOKEN}


@app.get("/health")
def health():
    return {"ok": True}


class Profile(BaseModel):
    members: int | None = Field(None, ge=1, le=20)
    sewer: bool | None = None
    ceb_tariff: str | None = None
    tv_licence: bool | None = None
    today: date | None = None

    @field_validator("ceb_tariff")
    @classmethod
    def tariff_ok(cls, v):
        if v is not None and v not in ("110", "120", "140"):
            raise ValueError("CEB tariff must be 110, 120 or 140 (see the 'Tariff' box on the CEB bill)")
        return v


@app.get("/household", dependencies=[Depends(auth)])
def get_household():
    h = store.load()
    return {k: h[k] for k in ("name", "members", "sewer", "ceb_tariff", "tv_licence", "today", "note")}


@app.put("/household", dependencies=[Depends(auth)])
def update_household(p: Profile):
    h = store.load()
    for k, v in p.model_dump(exclude_none=True).items():
        h[k] = v.isoformat() if isinstance(v, date) else v
    store.log(h, "profile_updated", fields=list(p.model_dump(exclude_none=True)))
    store.save(h)
    return get_household()


class BillIn(BaseModel):
    utility: str
    start: date
    end: date
    units: float = Field(..., ge=0, le=100000)

    @model_validator(mode="after")
    def check(self):
        if self.utility not in ("water", "electricity"):
            raise ValueError("utility must be 'water' or 'electricity'")
        if self.end <= self.start:
            raise ValueError(f"Bill end date ({self.end}) must be after its start date ({self.start})")
        if (self.end - self.start).days > 70:
            raise ValueError(f"Billing period is {(self.end - self.start).days} days; a CWA/CEB bill covers about one month")
        return self


@app.get("/bills", dependencies=[Depends(auth)])
def list_bills():
    return store.load()["bills"]


@app.post("/bills", dependencies=[Depends(auth)])
def add_bill(b: BillIn):
    h = store.load()
    for x in h["bills"]:
        if x["utility"] == b.utility and x.get("source") != "placeholder" and date.fromisoformat(x["start"]) < b.end and b.start < date.fromisoformat(x["end"]):
            err(409, "overlap", f"This {b.utility} bill overlaps the one from {x['start']} to {x['end']}. Correct the dates.")
    # the first real bill replaces the demo placeholders for that utility
    h["bills"] = [x for x in h["bills"] if not (x["utility"] == b.utility and x.get("source") == "placeholder")]
    h["bills"].append({"utility": b.utility, "start": b.start.isoformat(), "end": b.end.isoformat(), "units": b.units, "source": "entered"})
    store.log(h, "bill_added", utility=b.utility, start=b.start.isoformat(), end=b.end.isoformat(), units=b.units)
    store.save(h)
    return {"bills": h["bills"], "forecast": forecast(h, b.utility)}


@app.get("/utilities/history", dependencies=[Depends(auth)])
def history(utility: str, days: int = 90):
    if utility not in ("water", "electricity"):
        err(400, "validation_error", "utility must be 'water' or 'electricity'")
    return daily_history(store.load(), utility)[-max(1, min(days, 400)):]


@app.get("/utilities/forecast", dependencies=[Depends(auth)])
def utilities_forecast():
    h = store.load()
    return {u: forecast(h, u) for u in ("water", "electricity")}


@app.get("/actions/catalogue")
def catalogue():
    return [{"key": k, **v, "appliances_kw": actions.APPLIANCES_KW if k == "appliance_hours" else None} for k, v in actions.CATALOGUE.items()]


class ScenarioIn(BaseModel):
    action: str
    params: dict = {}


@app.post("/household/scenarios", dependencies=[Depends(auth)])
def scenarios(s: ScenarioIn):
    try:
        return advice.scenario(store.load(), s.action, s.params)
    except KeyError as e:
        err(400, "unknown_action", str(e).strip("'\""))


@app.post("/actions", dependencies=[Depends(auth)])
def select_action(s: ScenarioIn):
    if s.action not in actions.CATALOGUE:
        err(400, "unknown_action", f"Unknown action '{s.action}'")
    h = store.load()
    a = {"id": uuid.uuid4().hex[:8], "key": s.action, "utility": actions.CATALOGUE[s.action]["utility"],
         "params": s.params, "status": "selected", "selected_on": h["today"]}
    h.setdefault("actions", []).append(a)
    store.log(h, "action_selected", action=s.action, id=a["id"])
    store.save(h)
    return a


@app.post("/actions/{aid}/complete", dependencies=[Depends(auth)])
def complete_action(aid: str):
    h = store.load()
    a = next((x for x in h.get("actions", []) if x["id"] == aid), None)
    if a is None:
        err(404, "not_found", f"No action with id {aid}")
    if a["status"] == "completed":
        return a                                   # idempotent: completing twice changes nothing
    a["status"], a["completed_on"] = "completed", h["today"]
    store.log(h, "action_completed", action=a["key"], id=aid)
    store.save(h)
    return {**a, "forecast": forecast(h, a["utility"])}


@app.get("/household/insights", dependencies=[Depends(auth)])
def household_insights():
    return advice.insights(store.load())


@app.get("/activity", dependencies=[Depends(auth)])
def activity():
    return list(reversed(store.load().get("activity", [])))


@app.post("/demo/reset", dependencies=[Depends(auth)])
def demo_reset():
    store.reset()
    return {"ok": True}
