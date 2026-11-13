"""Electricity module routes. Everything lives under /electricity so it can sit next to /water and /food.

Errors: {"detail": {"code", "message", "details"}}; validation errors are HTTP 422 with a specific message.
"""
import uuid
from datetime import date
from datetime import date as Date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from . import actions, advice, store, tariff
from .auth import err, require_login
from .forecast import add_forecast_checks_for_bill, forecast, save_forecast_snapshot
from .history import daily_history, today

try:                                   # merged backend: also write shared tables (core/sync.py)
    from core import sync
except ImportError:
    sync = None

router = APIRouter(prefix="/electricity", tags=["electricity"], dependencies=[Depends(require_login)])


def _ok_or_422(fn, *a):
    try:
        return fn(*a)
    except KeyError as e:
        err(400, "unknown_action", str(e).strip("'\""))
    except ValueError as e:
        err(422, "validation_error", str(e))


# ---------- profile (onboarding) ----------
class Profile(BaseModel):
    members: int | None = Field(None, ge=1, le=20)
    ceb_tariff: Literal["110", "120", "140"] | None = Field(None, description="The 'Tariff' box on the CEB bill")
    tv_licence: bool | None = Field(None, description="TV licence fee (Rs 150) is on the CEB bill")
    monthly_budget_rs: float | None = Field(None, ge=0, le=100000)
    today: date | None = Field(None, description="Demo only: the date the app treats as today")


@router.get("/profile")
def get_profile():
    s = store.load()
    return {**s["profile"], "today": today(s).isoformat()}


@router.put("/profile")
def update_profile(p: Profile):
    s = store.load()
    changes = p.model_dump(exclude_unset=True)
    if "today" in changes:
        s["today"] = changes.pop("today").isoformat() if changes["today"] else None
    s["profile"].update(changes)
    store.log(s, "profile_updated", fields=sorted(p.model_dump(exclude_unset=True)))
    store.save(s)
    return get_profile()


# ---------- electricity assessment ----------
@router.get("/assessment")
def get_assessment():
    return store.load().get("assessment", {})


@router.put("/assessment")
def update_assessment(payload: dict):
    s = store.load()
    s["assessment"] = {**s.get("assessment", {}), **payload}
    store.log(s, "assessment_updated", fields=sorted(payload.keys()))
    store.save(s)
    return s["assessment"]


# ---------- bills (numbers from the OCR team or typed in) ----------
class BillIn(BaseModel):
    start: date
    end: date
    kwh: float = Field(..., ge=0, le=100000)
    amount_rs: float | None = Field(None, ge=0, le=100000)
    tariff_class: Literal["110", "120", "140"] | None = Field(None)
    start_reading: float | None = Field(None, ge=0)
    end_reading: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def check(self):
        if self.end <= self.start:
            raise ValueError(f"Bill end date ({self.end}) must be after its start date ({self.start})")
        if (self.end - self.start).days > 70:
            raise ValueError(f"Billing period is {(self.end - self.start).days} days; a CEB bill covers about one month")
        if self.start_reading is not None and self.end_reading is not None:
            if self.end_reading < self.start_reading:
                raise ValueError("end_reading must be higher than start_reading")
            if abs((self.end_reading - self.start_reading) - self.kwh) > 1:
                raise ValueError(f"Readings give {self.end_reading - self.start_reading:g} kWh but the bill says {self.kwh:g} kWh. Check the numbers.")
        return self


@router.get("/bills")
def list_bills():
    return sorted(store.load()["bills"], key=lambda b: b["start"])


@router.post("/bills")
def add_bill(b: BillIn):
    s = store.load()
    if b.end > today(s):
        err(422, "validation_error", f"Bill end date {b.end} is in the future")
    for x in s["bills"]:
        if x.get("source") != "placeholder" and date.fromisoformat(x["start"]) < b.end and b.start < date.fromisoformat(x["end"]):
            err(409, "overlap", f"This bill overlaps the one from {x['start']} to {x['end']}. Correct the dates or delete that bill.")
    s["bills"] = [x for x in s["bills"] if x.get("source") != "placeholder"]   # the first real bill replaces the demo ones
    bill = {
        "id": uuid.uuid4().hex[:8],
        "start": b.start.isoformat(),
        "end": b.end.isoformat(),
        "kwh": b.kwh,
        "amount_rs": b.amount_rs,
        "tariff_class": b.tariff_class or s.get("profile", {}).get("ceb_tariff"),
        "end_reading": b.end_reading,
        "source": "entered"
    }
    if b.amount_rs is not None:
        expected_total = tariff.electricity_bill(
            b.kwh,
            tariff_code=bill["tariff_class"] or "140",
            tv_licence=s.get("profile", {}).get("tv_licence", True),
        ).total
        difference = abs(expected_total - b.amount_rs)
        bill["amount_check"] = {
            "calculated_total_rs": round(expected_total, 2),
            "difference_rs": round(difference, 2),
            "status": "ok" if difference <= 5 else "mismatch",
        }
    if sync:
        amount = b.amount_rs if b.amount_rs is not None else tariff.electricity_bill(
            b.kwh, tariff_code=bill["tariff_class"] or "140", tv_licence=s.get("profile", {}).get("tv_licence", True)).total
        bill["db_id"] = sync.mirror_bill("electricity", bill["start"], bill["end"], b.kwh, amount,
                                         f"CEB {bill['tariff_class'] or '140'}" + ("" if b.amount_rs is not None else
                                                                                  " (amount = tariff calculation)"), bill["id"])
    s["bills"].append(bill)
    latest_end = max(x["end"] for x in s["bills"])
    dropped = [r["id"] for r in s.get("readings", []) if r["date"] <= latest_end]
    s["readings"] = [r for r in s.get("readings", []) if r["date"] > latest_end]   # now inside a billed period
    if dropped:
        store.log(s, "readings_replaced_by_bill", ids=dropped)
    store.log(s, "bill_added", id=bill["id"], start=bill["start"], end=bill["end"], kwh=b.kwh)
    add_forecast_checks_for_bill(s, bill)
    store.save(s)
    return {"bill": bill, "forecast": forecast(s)}


@router.delete("/bills/{bill_id}")
def delete_bill(bill_id: str):
    s = store.load()
    if not any(x["id"] == bill_id for x in s["bills"]):
        err(404, "not_found", f"No bill with id {bill_id}")
    if sync:
        sync.remove_bill(next(x for x in s["bills"] if x["id"] == bill_id).get("db_id"))
    s["bills"] = [x for x in s["bills"] if x["id"] != bill_id]
    store.log(s, "bill_deleted", id=bill_id)
    store.save(s)
    return {"ok": True}


# ---------- meter readings (between bills: real data for the current cycle) ----------
class ReadingIn(BaseModel):
    date: Date
    index_kwh: float = Field(..., ge=0, le=10_000_000, description="The digits on the CEB meter (kWh)")


@router.get("/readings")
def list_readings():
    return sorted(store.load().get("readings", []), key=lambda r: r["date"])


@router.post("/readings")
def add_reading(r: ReadingIn):
    s = store.load()
    if r.date > today(s):
        err(422, "validation_error", f"Reading date {r.date} is in the future")
    bills = sorted(s["bills"], key=lambda b: b["end"])
    if bills and r.date <= date.fromisoformat(bills[-1]["end"]):
        err(422, "validation_error", f"Readings are for after the last bill (which ends {bills[-1]['end']}).")
    if any(x["date"] == r.date.isoformat() for x in s.get("readings", [])):
        err(409, "duplicate", f"There is already a reading for {r.date}. Delete it first.")
    earlier = [x for x in s.get("readings", []) if x["date"] < r.date.isoformat()]
    floor = max([x["index_kwh"] for x in earlier] + ([bills[-1]["end_reading"]] if bills and bills[-1].get("end_reading") is not None else []), default=None)
    if floor is not None and r.index_kwh < floor:
        err(422, "validation_error", f"The meter cannot go backwards: {r.index_kwh:g} is below the previous reading {floor:g}.")
    later = [x for x in s.get("readings", []) if x["date"] > r.date.isoformat()]
    if later and r.index_kwh > min(x["index_kwh"] for x in later):
        err(422, "validation_error", "This reading is higher than a later reading. Check the date and number.")
    reading = {"id": uuid.uuid4().hex[:8], "date": r.date.isoformat(), "index_kwh": r.index_kwh}
    if sync:
        reading["db_id"] = sync.mirror_reading("electricity", r.index_kwh, reading["date"])
    s.setdefault("readings", []).append(reading)
    store.log(s, "reading_added", id=reading["id"], date=reading["date"], index_kwh=r.index_kwh)
    store.save(s)
    return {"reading": reading, "forecast": forecast(s)}


@router.delete("/readings/{reading_id}")
def delete_reading(reading_id: str):
    s = store.load()
    if not any(x["id"] == reading_id for x in s.get("readings", [])):
        err(404, "not_found", f"No reading with id {reading_id}")
    s["readings"] = [x for x in s["readings"] if x["id"] != reading_id]
    store.log(s, "reading_deleted", id=reading_id)
    store.save(s)
    return {"ok": True}


# ---------- history, forecast, insights ----------
@router.get("/history")
def history(days: int = 90):
    return daily_history(store.load())[-max(1, min(days, 400)):]


@router.get("/forecast")
def get_forecast():
    s = store.load()
    f = forecast(s)
    if f.get("status") == "ok":
        save_forecast_snapshot(s, f)
        store.save(s)
    return f


@router.get("/forecast-checks")
def get_forecast_checks():
    return store.load().get("forecast_checks", [])


@router.get("/insights")
def get_insights():
    return advice.insights(store.load())


@router.get("/summary")
def get_summary():
    """Shared module contract, read by the Household AI."""
    s = store.load()
    f = forecast(s)
    if f.get("status") == "ok":
        save_forecast_snapshot(s, f)
        store.save(s)
    return advice.summary(s)


# ---------- actions ----------
@router.get("/actions/catalogue")
def catalogue():
    return [{"key": k, **{x: v[x] for x in ("title", "params", "formula", "assumptions")},
             "limits": {n: list(r) for n, r in v["limits"].items()}} for k, v in actions.CATALOGUE.items()]


class ActionIn(BaseModel):
    action: str
    params: dict = {}


@router.post("/scenarios")
def scenarios(a: ActionIn):
    return _ok_or_422(advice.scenario, store.load(), a.action, a.params)


@router.get("/actions")
def list_actions():
    return store.load().get("actions", [])


@router.post("/actions")
def select_action(a: ActionIn):
    s = store.load()
    p = _ok_or_422(actions.resolved_params, a.action, a.params, s["profile"])
    existing = next((x for x in s.get("actions", []) if x["key"] == a.action and x["status"] == "selected"), None)
    if existing:                                             # selecting the same action twice: one record
        existing["params"] = p
        store.save(s)
        return existing
    rec = {"id": uuid.uuid4().hex[:8], "key": a.action, "params": p, "status": "selected", "selected_on": today(s).isoformat()}
    if sync:
        rec["db_id"] = sync.mirror_action("electricity", a.action, p, "selected")
    s.setdefault("actions", []).append(rec)
    store.log(s, "action_selected", action=a.action, id=rec["id"])
    store.save(s)
    return rec


@router.post("/actions/{action_id}/complete")
def complete_action(action_id: str):
    s = store.load()
    a = next((x for x in s.get("actions", []) if x["id"] == action_id), None)
    if a is None:
        err(404, "not_found", f"No action with id {action_id}")
    if a["status"] != "completed":                           # idempotent: completing twice changes nothing
        a["status"], a["completed_on"] = "completed", today(s).isoformat()
        if sync:
            sync.mirror_action("electricity", a["key"], a.get("params"), "completed", a.get("db_id"))
        store.log(s, "action_completed", action=a["key"], id=action_id)
        store.save(s)
    return {**a, "forecast": forecast(s)}


@router.get("/activity")
def activity():
    return list(reversed(store.load().get("activity", [])))


@router.post("/activity")
def add_activity(payload: dict):
    s = store.load()
    event = payload.get("event") or payload.get("name") or "manual_event"
    details = payload.get("details", {}) if isinstance(payload.get("details", {}), dict) else {}
    store.log(s, event, **details)
    store.save(s)
    return {"ok": True, "event": event, "activity": list(reversed(s.get("activity", [])))[:1]}


@router.post("/demo/reset")
def demo_reset():
    store.reset()
    return {"ok": True}
