"""Water module routes, all under /water (module contract). Login: see auth.py.

Errors: {"detail": {"code", "message", "details"}}. Not having enough data is NOT an error: the response has
status "insufficient_data" / "needs_input" / "needs_readings" with the message to show.
Every change is written to the activity log; the forecast is rebuilt from the saved records each time.
"""
import uuid
from datetime import date
from datetime import date as Date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from . import advice, store
from . import assessment as A
from . import forecast as F
from . import scenarios as SC
from .auth import err, require_login

try:                                   # merged backend: also write shared tables (core/sync.py)
    from core import sync
except ImportError:
    sync = None

router = APIRouter(prefix="/water", tags=["water"], dependencies=[Depends(require_login)])


def _guard(fn, *a):
    try:
        return fn(*a)
    except KeyError as e:
        err(400, "unknown_item", str(e).strip("'\""))
    except ValueError as e:
        err(422, "validation_error", str(e))


# ---------- onboarding: general questions (shared) and profile ----------
@router.get("/onboarding/questions")
def onboarding_questions():
    return {"general": A.GENERAL, "general_required": True,
            "water": {k: {**v, "options": list(v["options"])} for k, v in A.QUESTIONS.items()}, "water_required": False,
            "mauritius_defaults": A.MAURITIUS_DEFAULTS}


@router.get("/household")
def get_household():
    s = store.load()
    h = s["household"]
    return {**h, "complete": all(h.get(k) for k in A.GENERAL),
            "note": "Shared general answers (stored by the team backend; copy kept so this module runs alone)."}


@router.put("/household")
def put_household(body: dict):
    s = store.load()
    s["household"].update(_guard(A.validate_general, body))
    store.log(s, "household_answered", fields=sorted(body))
    store.save(s)
    return get_household()


class Profile(BaseModel):
    sewer: bool | None = Field(None, description="Connected to the public sewer (adds wastewater charges)")
    region: Literal["North", "South", "East", "West", "Centre"] | None = None
    has_air_conditioning: bool | None = None
    monthly_budget_rs: float | None = Field(None, ge=0, le=100000)
    today: Date | None = Field(None, description="Demo only: the date the app treats as today")


@router.get("/profile")
def get_profile():
    s = store.load()
    return {**s["profile"], "today": F.today(s).isoformat()}


@router.put("/profile")
def put_profile(p: Profile):
    s = store.load()
    changes = p.model_dump(exclude_unset=True)
    if "today" in changes:
        s["today"] = changes.pop("today").isoformat() if changes["today"] else None
    s["profile"].update(changes)
    store.log(s, "profile_updated", fields=sorted(p.model_dump(exclude_unset=True)))
    store.save(s)
    return get_profile()


# ---------- optional water assessment (versioned) ----------
@router.get("/assessment")
def get_assessment():
    s = store.load()
    latest = A.latest(s)
    return {**latest, "complete": A.complete(s),
            "unknown": [k for k in A.QUESTIONS if not A.known(s, k)],
            "message": None if A.complete(s) else F.MESSAGES["assessment_prompt"]}


@router.put("/assessment")
def put_assessment(answers: dict):
    """Partial answers allowed (skip / resume). Each save creates a new version."""
    s = store.load()
    v = _guard(A.save_version, s, answers)
    store.log(s, "assessment_answered", version=v["version"], fields=sorted(answers))
    store.save(s)
    return {**v, "complete": A.complete(s), "message": F.MESSAGES["after_assessment"]}


@router.get("/assessment/versions")
def assessment_versions():
    return store.load().get("assessments", [])


# ---------- bills (values the user CONFIRMED after OCR or typed in) ----------
class BillIn(BaseModel):
    start: Date
    end: Date
    m3: float = Field(..., ge=0, le=10000)
    amount_rs: float | None = Field(None, ge=0, le=1_000_000, description="Amount printed on the bill")
    start_reading: float | None = Field(None, ge=0)
    end_reading: float | None = Field(None, ge=0)
    ocr_id: str | None = Field(None, description="Id from the OCR service, kept for provenance")

    @model_validator(mode="after")
    def check(self):
        if self.end <= self.start:
            raise ValueError(f"Bill end date ({self.end}) must be after its start date ({self.start})")
        if not 10 <= (self.end - self.start).days <= 70:
            raise ValueError(f"Billing period is {(self.end - self.start).days} days; a CWA bill covers about one month")
        if self.start_reading is not None and self.end_reading is not None:
            if self.end_reading < self.start_reading:
                raise ValueError("end_reading must be higher than start_reading")
            if abs((self.end_reading - self.start_reading) - self.m3) > 1:
                raise ValueError(f"Readings give {self.end_reading - self.start_reading:g} m3 but the bill says "
                                 f"{self.m3:g} m3. Check the numbers.")
        return self


@router.get("/bills")
def list_bills():
    s = store.load()
    return [{**b, "litres_per_day": round(float(b["m3"]) * 1000 / F.days_of(b)), "days": F.days_of(b),
             "tariff_check": advice.tariff_check(s, b)} for b in F.bills(s)]


def _save_bill(s, b: BillIn, replace_id=None):
    if b.end > F.today(s):
        err(422, "validation_error", f"Bill end date {b.end} is in the future")
    for x in s["bills"]:
        if x["id"] != replace_id and date.fromisoformat(x["start"]) < b.end and b.start < date.fromisoformat(x["end"]):
            err(409, "overlap", f"This bill overlaps the one from {x['start']} to {x['end']}. "
                                "Correct the dates, or replace that bill on purpose.", {"bill_id": x["id"]})
    bill = {"id": replace_id or uuid.uuid4().hex[:8], "start": b.start.isoformat(), "end": b.end.isoformat(),
            "m3": b.m3, "amount_rs": b.amount_rs, "start_reading": b.start_reading, "end_reading": b.end_reading,
            "ocr_id": b.ocr_id, "source": "confirmed"}
    old = next((x for x in s["bills"] if x["id"] == replace_id), None)
    if sync:
        if old:
            sync.remove_bill(old.get("db_id"))
        from .tariff import water_bill
        amount = b.amount_rs if b.amount_rs is not None else water_bill(b.m3, s["profile"].get("sewer") or False).total
        bill["db_id"] = sync.mirror_bill("water", bill["start"], bill["end"], b.m3, amount,
                                         "CWA domestic" + ("" if b.amount_rs is not None else " (amount = tariff calculation)"),
                                         bill["id"])
    s["bills"] = [x for x in s["bills"] if x["id"] != replace_id] + [bill]
    chk = F.check_against_forecast(s, bill) if not replace_id else None
    latest_end = max(x["end"] for x in s["bills"])
    s["readings"] = [r for r in s.get("readings", []) if r["date"] > latest_end]
    store.log(s, "bill_replaced" if replace_id else "bill_confirmed", id=bill["id"], start=bill["start"],
              end=bill["end"], m3=b.m3, ocr_id=b.ocr_id)
    if chk:
        store.log(s, "forecast_checked", forecast_id=chk["forecast_id"], bill_id=bill["id"], error_pct=chk["error_pct"])
    snap = F.snapshot(s, reason=f"after bill {bill['id']}")
    if snap:
        store.log(s, "forecast_issued", id=snap["id"], period_start=snap["period_start"], m3=snap["estimated_units"])
    store.save(s)
    return {"bill": bill, "tariff_check": advice.tariff_check(s, bill), "forecast_check": chk, "forecast": F.forecast(s)}


@router.post("/bills")
def add_bill(b: BillIn):
    return _save_bill(store.load(), b)


@router.put("/bills/{bill_id}")
def replace_bill(bill_id: str, b: BillIn):
    s = store.load()
    if not any(x["id"] == bill_id for x in s["bills"]):
        err(404, "not_found", f"No bill with id {bill_id}")
    return _save_bill(s, b, replace_id=bill_id)


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


# ---------- meter readings ----------
class ReadingIn(BaseModel):
    date: Date
    index_m3: float = Field(..., ge=0, le=10_000_000, description="The black digits on the CWA meter (m3)")


@router.get("/readings")
def list_readings():
    return sorted(store.load().get("readings", []), key=lambda r: r["date"])


@router.post("/readings")
def add_reading(r: ReadingIn):
    s = store.load()
    if r.date > F.today(s):
        err(422, "validation_error", f"Reading date {r.date} is in the future")
    bl = F.bills(s)
    if bl and r.date <= date.fromisoformat(bl[-1]["end"]):
        err(422, "validation_error", f"Readings are for after your last bill (which ends {bl[-1]['end']}).")
    if any(x["date"] == r.date.isoformat() for x in s.get("readings", [])):
        err(409, "duplicate", f"There is already a reading for {r.date}. Delete it first.")
    earlier = [x["index_m3"] for x in s.get("readings", []) if x["date"] < r.date.isoformat()]
    if bl and bl[-1].get("end_reading") is not None:
        earlier.append(bl[-1]["end_reading"])
    if earlier and r.index_m3 < max(earlier):
        err(422, "validation_error", f"The meter cannot go backwards: {r.index_m3:g} is below the previous reading {max(earlier):g}.")
    later = [x["index_m3"] for x in s.get("readings", []) if x["date"] > r.date.isoformat()]
    if later and r.index_m3 > min(later):
        err(422, "validation_error", "This reading is higher than a later reading. Check the date and number.")
    reading = {"id": uuid.uuid4().hex[:8], "date": r.date.isoformat(), "index_m3": r.index_m3}
    if sync:
        reading["db_id"] = sync.mirror_reading("water", r.index_m3, reading["date"])
    s.setdefault("readings", []).append(reading)
    store.log(s, "reading_added", id=reading["id"], date=reading["date"], index_m3=r.index_m3)
    store.save(s)
    return {"reading": reading, "current_cycle": F.current_cycle(s)}


@router.delete("/readings/{reading_id}")
def delete_reading(reading_id: str):
    s = store.load()
    if not any(x["id"] == reading_id for x in s.get("readings", [])):
        err(404, "not_found", f"No reading with id {reading_id}")
    if sync:
        sync.remove_reading(next(x for x in s["readings"] if x["id"] == reading_id).get("db_id"))
    s["readings"] = [x for x in s["readings"] if x["id"] != reading_id]
    store.log(s, "reading_deleted", id=reading_id)
    store.save(s)
    return {"ok": True}


# ---------- forecast, history, checks ----------
@router.get("/forecast")
def get_forecast():
    """Next billing cycle (spec: next_N_day_cycle)."""
    return F.forecast(store.load())


@router.get("/forecast/current")
def get_current_cycle():
    """This month so far: only with dated meter readings."""
    return F.current_cycle(store.load())


@router.get("/history")
def history():
    """For the chart: actual bills vs saved estimates (never made-up daily values)."""
    s = store.load()
    return {"actual_bills": [{"id": b["id"], "start": b["start"], "end": b["end"], "m3": b["m3"],
                              "litres_per_day": round(float(b["m3"]) * 1000 / F.days_of(b)), "kind": "actual"}
                             for b in F.bills(s)],
            "estimates": [{**{k: f[k] for k in ("id", "issued_on", "period_start", "period_end", "estimated_units",
                                                "range", "cost_rs", "status")}, "kind": "forecast"}
                          for f in s.get("forecasts", [])],
            "checks": F.all_checks(s)}


@router.get("/checks")
def checks():
    """Bill vs prediction: real checks (saved forecast vs later bill) and back-tests (each bill from earlier bills)."""
    s = store.load()
    return {"checks": F.all_checks(s), "reliability": F.reliability(s)}


# ---------- what-if ----------
@router.get("/scenarios/catalogue")
def scenario_catalogue():
    s = store.load()
    out = []
    for k, v in SC.CATALOGUE.items():
        _, _, missing = _guard(SC.resolve, s, k, {})
        out.append({"key": k, "title": v["title"], "direction": v["direction"], "formula": v["formula"],
                    "params": v["params"], "needs": v["needs"],
                    "ready": not [m for m in missing if m["item"] not in v["params"]],
                    "missing": missing})
    return out


class ScenarioIn(BaseModel):
    scenario: str
    params: dict = {}


@router.post("/scenarios")
def run_scenario(x: ScenarioIn):
    s = store.load()
    r = _guard(SC.run, s, x.scenario, x.params)
    s.setdefault("scenario_runs", []).append({k: r.get(k) for k in ("id", "scenario", "params", "status", "difference")})
    s["scenario_runs"] = s["scenario_runs"][-30:]
    store.log(s, "scenario_run", id=r["id"], scenario=x.scenario, status=r["status"])
    store.save(s)
    return r


# ---------- goals / actions ----------
@router.get("/actions")
def list_actions():
    return store.load().get("actions", [])


@router.post("/actions")
def save_goal(x: ScenarioIn):
    """'Save as goal'. Only per-day scenarios that have all their data can become goals."""
    s = store.load()
    if x.scenario not in SC.CATALOGUE:
        err(400, "unknown_item", f"Unknown scenario '{x.scenario}'")
    if SC.CATALOGUE[x.scenario]["type"] != "per_day":
        err(422, "validation_error", "Only habit changes (per-day scenarios) can be saved as goals.")
    _, _, missing = _guard(SC.resolve, s, x.scenario, x.params)
    if missing:
        err(422, "needs_input", "Not enough data to save this goal. " + " ".join(m["prompt"] for m in missing), {"missing": missing})
    existing = next((a for a in s.get("actions", []) if a["key"] == x.scenario and a["status"] == "selected"), None)
    if existing:
        existing["params"] = x.params
        store.save(s)
        return existing
    a = {"id": uuid.uuid4().hex[:8], "key": x.scenario, "params": x.params, "status": "selected",
         "selected_on": F.today(s).isoformat()}
    if sync:
        a["db_id"] = sync.mirror_action("water", x.scenario, x.params, "selected")
    s.setdefault("actions", []).append(a)
    store.log(s, "scenario_saved_as_goal", id=a["id"], scenario=x.scenario)
    store.save(s)
    return a


@router.post("/actions/{action_id}/complete")
def complete_action(action_id: str):
    s = store.load()
    a = next((x for x in s.get("actions", []) if x["id"] == action_id), None)
    if a is None:
        err(404, "not_found", f"No action with id {action_id}")
    if a["status"] != "completed":                     # idempotent: completing twice changes nothing
        a["status"], a["completed_on"] = "completed", F.today(s).isoformat()
        if sync:
            sync.mirror_action("water", a["key"], a["params"], "completed", a.get("db_id"))
        store.log(s, "action_completed", id=action_id, scenario=a["key"])
        store.save(s)
    return {**a, "forecast": F.forecast(s)}


# ---------- insights, context, summary, activity ----------
@router.get("/insights")
def get_insights():
    return advice.insights(store.load())


@router.get("/seasons")
def get_seasons():
    return advice.year_outlook(store.load())


@router.get("/context")
def get_context():
    return advice.context(store.load())


@router.get("/completeness")
def get_completeness():
    s = store.load()
    return {"data_completeness": F.completeness(s), "reliability": F.reliability(s),
            "note": "Completeness = what you told us. Reliability = how well past estimates matched real bills. "
                    "Answering questions raises completeness, not reliability."}


@router.get("/summary")
def get_summary():
    """Module contract read by the lead AI."""
    return advice.summary(store.load())


@router.get("/activity")
def activity():
    return list(reversed(store.load().get("activity", [])))


@router.post("/demo/reset")
def demo_reset(sample: bool = False):
    """Empty account (default), or ?sample=true for the FICTIONAL sample household used to rehearse the demo."""
    s = store.reset(sample=sample)
    return {"ok": True, "sample": sample, "note": s.get("note")}
