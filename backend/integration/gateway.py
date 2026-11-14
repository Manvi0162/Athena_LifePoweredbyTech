"""The routes the Expo app calls (livebetter/API_HANDOFF.md + src/api.ts), connected to the real modules.

  POST /households/onboarding   household profile -> shared households row (+ water/electricity copies)
  GET  /households/me           the household for the app's state
  GET/POST /bills, DELETE /bills/{kind}/{id}   -> water or electricity engine (tariff check, forecast snapshot)
  GET  /utilities/forecast?category=water|electricity
  POST /household/scenarios     {category, reduction_percent} or {category, scenario, params}
  GET  /household/insights      Big Brain dashboard in the app's Insight shape
  GET  /household/dashboard     Big Brain dashboard exactly as in the Big Brain report (section 6)
  GET  /big-brain/dashboard     Big Brain v3 (Manvi's latest notebook): savings compared per 30 days + summary
  POST /household/coach         AI coach answer
  GET  /activity                every module's events, newest first
  POST /demo/sample, /demo/reset
Nothing here calculates usage or money: it routes to the module that owns the calculation.
"""
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from core.identity import CURRENT, err, forget_household, household, require_context, require_household

router = APIRouter(tags=["app"])
CONF = {"insufficient_data": "unavailable", "preliminary": "limited_history", "better_supported": "historical_baseline"}
ELEC_TARIFFS = {"110", "120", "140"}


# ---------------- household ----------------
class Onboarding(BaseModel):
    name: str = Field(default="My household", min_length=1, max_length=80)
    members: int = Field(ge=1, le=30)
    home_type: str = "House"
    water_tariff: str = "Domestic"
    electricity_tariff: str = "Domestic"
    monthly_target: float = Field(default=0, ge=0, le=10_000_000)
    diet: str = "No preference"
    allergies: str = ""
    water_habit: str = ""
    appliance_notes: str = ""
    occupancy: str | None = None
    main_goal: str | None = None
    region: str | None = None
    water_budget: float | None = Field(default=None, ge=0)
    electricity_budget: float | None = Field(default=None, ge=0)


def ui_household(h):
    if not h:
        return None
    p, g = h.get("preferences") or {}, h.get("budget_goals") or {}
    return {"id": h["id"], "name": h.get("name"), "members": h.get("members"), "home_type": p.get("home_type", "House"),
            "water_tariff": p.get("water_tariff", "Domestic"), "electricity_tariff": p.get("electricity_tariff", "Domestic"),
            "monthly_target": g.get("monthly_target", 0), "diet": p.get("diet", "No preference"),
            "allergies": p.get("allergies", ""), "water_habit": p.get("water_habit", ""),
            "appliance_notes": p.get("appliance_notes", ""), "occupancy": p.get("occupancy"),
            "main_goal": p.get("main_goal"), "region": p.get("region")}


@router.post("/households/onboarding")
def onboarding(body: Onboarding, x_step_up: str | None = Header(default=None)):
    ctx = require_context()
    if household(ctx) is not None:                       # changing an existing household needs the pattern
        from core.security import require_step_up
        require_step_up(ctx, "edit_household", x_step_up)
    prefs = {k: getattr(body, k) for k in ("home_type", "water_tariff", "electricity_tariff", "diet", "allergies",
                                           "water_habit", "appliance_notes", "occupancy", "main_goal", "region")}
    goals = {"monthly_target": body.monthly_target, "water_budget": body.water_budget,
             "electricity_budget": body.electricity_budget}
    h = household(ctx)
    row = {"name": body.name.strip(), "members": body.members, "currency": "MUR", "preferences": prefs,
           "budget_goals": goals}
    if h:
        ctx.db.table("households").update(row).eq("id", h["id"]).execute()
        event = "household_updated"
    else:
        h = ctx.db.table("households").insert({**row, "owner_id": ctx.user_id}).execute().data[0]
        event = "household_created"
    forget_household(ctx)
    h = household(ctx)
    ctx.db.table("activity_logs").insert({"household_id": h["id"], "event_type": event,
                                          "details": {"members": body.members, "home_type": body.home_type}}).execute()
    if body.electricity_tariff.strip() in ELEC_TARIFFS:     # the CEB tariff box, if the user gave it
        from electricity import store as estore
        s = estore.load()
        s.setdefault("profile", {})["ceb_tariff"] = body.electricity_tariff.strip()
        estore.save(s)
    return {"id": h["id"], "household": ui_household(h)}


@router.get("/households/me")
def me():
    ctx = require_context()
    h = household(ctx)
    if not h:
        err(404, "no_household", "No household yet. Complete onboarding.")
    return {"id": h["id"], "household": ui_household(h), "mode": ctx.mode}


# ---------------- bills ----------------
class UIBill(BaseModel):
    kind: str
    period_start: date
    period_end: date
    units: float = Field(gt=0)            # a 0 m3 / 0 kWh bill is a typing mistake, not a bill
    amount: float | None = Field(default=None, ge=0)
    tariff: str | None = None
    start_reading: float | None = None
    end_reading: float | None = None
    ocr_id: str | None = None
    household_id: str | None = None
    currency: str | None = None


def _validation(exc: ValidationError):
    msg = exc.errors()[0].get("msg", "Invalid input").replace("Value error, ", "")
    raise HTTPException(422, {"code": "validation_error", "message": msg, "details": {}})


@router.post("/bills")
def add_bill(b: UIBill):
    require_household()
    if b.amount == 0:                     # CWA and CEB always charge something: Rs 0 means "not entered"
        b.amount = None
    if b.kind == "water":
        from water import api as wapi
        from water import store as wstore
        try:
            body = wapi.BillIn(start=b.period_start, end=b.period_end, m3=b.units, amount_rs=b.amount,
                               start_reading=b.start_reading, end_reading=b.end_reading, ocr_id=b.ocr_id)
        except ValidationError as exc:
            _validation(exc)
        r = wapi._save_bill(wstore.load(), body)
        return {"bill": _ui_bill("water", r["bill"]), "tariff_check": r["tariff_check"],
                "forecast_check": r["forecast_check"], "forecast": forecast_for_ui("water")}
    if b.kind == "electricity":
        from electricity import api as eapi
        try:
            body = eapi.BillIn(start=b.period_start, end=b.period_end, kwh=b.units, amount_rs=b.amount,
                               tariff_class=b.tariff if (b.tariff or "").strip() in ELEC_TARIFFS else None,
                               start_reading=b.start_reading, end_reading=b.end_reading)
        except ValidationError as exc:
            _validation(exc)
        r = eapi.add_bill(body)
        return {"bill": _ui_bill("electricity", r["bill"]), "tariff_check": r["bill"].get("amount_check"),
                "forecast": forecast_for_ui("electricity")}
    err(422, "validation_error", "kind must be 'water' or 'electricity'")


def _ui_bill(kind, b):
    units = b.get("m3") if kind == "water" else b.get("kwh")
    amount = b.get("amount_rs")
    source = "bill"
    if amount is None:
        if kind == "water":
            from water.tariff import water_bill
            amount, source = water_bill(float(units)).total, "tariff_calculation"
        else:
            from electricity.tariff import electricity_bill
            amount, source = electricity_bill(float(units), b.get("tariff_class") or "140").total, "tariff_calculation"
    return {"id": f"{kind}:{b['id']}", "household_id": (household(CURRENT.get()) or {}).get("id"), "kind": kind,
            "period_start": b["start"], "period_end": b["end"], "units": units, "amount": amount,
            "amount_source": source, "tariff": b.get("tariff_class") or ("CWA domestic" if kind == "water" else "CEB"),
            "currency": "MUR", "source": b.get("source")}


@router.get("/bills")
def list_bills(category: str | None = Query(default=None)):
    require_household()
    from electricity import store as estore
    from water import store as wstore
    out = []
    if category in (None, "water"):
        out += [_ui_bill("water", b) for b in wstore.load().get("bills", [])]
    if category in (None, "electricity"):
        out += [_ui_bill("electricity", b) for b in estore.load().get("bills", [])]
    return sorted(out, key=lambda b: (b["kind"], b["period_start"]))


@router.delete("/bills/{kind}/{bill_id}")
def delete_bill(kind: str, bill_id: str, x_step_up: str | None = Header(default=None)):
    ctx, _ = require_household()
    from core.security import require_step_up
    require_step_up(ctx, "delete_bill", x_step_up)        # misuse safeguard: a bill is evidence
    if kind == "water":
        from water import api as wapi
        return wapi.remove_bill(bill_id)
    if kind == "electricity":
        from electricity import api as eapi
        return eapi.remove_bill(bill_id)
    err(404, "not_found", "Unknown bill kind")


# ---------------- forecasts ----------------
def forecast_for_ui(kind):
    if kind == "water":
        from water import forecast as wf
        from water import store as wstore
        f = wf.forecast(wstore.load())
        base = {"category": "water", "unit": "m³", "currency": "MUR", "status": f["status"],
                "status_message": f["status_message"], "data_completeness": f["data_completeness"],
                "reliability": f["reliability"], "prompts": f.get("prompts", [])}
        if f["estimated_units"] is None:
            return {**base, "period_start": None, "period_end": None, "units": 0, "value": None, "confidence": "unavailable",
                    "method": f["status_message"], "assumptions": ["No confirmed water bill yet."], "source_data": []}
        return {**base, "period_start": f["period_start"], "period_end": f["period_end"], "units": f["estimated_units"],
                "value": f["cost"]["rs"], "range": f["range"],
                "cost_range": {"low": f["cost"]["low_rs"], "high": f["cost"]["high_rs"]},
                "confidence": CONF[f["status"]], "method": f["method_explained"], "assumptions": f["assumptions"],
                "source_data": f["source_ids"], "lines": f["lines"], "bill_breakdown": f["cost"]["breakdown"],
                "cost_note": f["cost"]["note"]}
    if kind == "electricity":
        from electricity import forecast as ef
        from electricity import store as estore
        f = ef.forecast(estore.load())
        fs = f.get("forecast_status", "insufficient_data")
        base = {"category": "electricity", "unit": "kWh", "currency": "MUR", "status": fs,
                "status_message": f.get("message") or f.get("status_message"),
                "data_completeness": f.get("data_completeness")}
        if f.get("status") != "ok":
            return {**base, "period_start": None, "period_end": None, "units": 0, "value": None, "confidence": "unavailable",
                    "method": f.get("message", "Add a confirmed electricity bill."),
                    "assumptions": ["No confirmed electricity bill yet."], "source_data": []}
        return {**base, "period_start": f["period_start"], "period_end": f["period_end"], "units": f["kwh"]["mid"],
                "value": f["cost_rs"]["mid"], "range": {"low": f["kwh"]["low"], "high": f["kwh"]["high"]},
                "cost_range": {"low": f["cost_rs"]["low"], "high": f["cost_rs"]["high"]},
                "confidence": CONF.get(fs, "limited_history"), "method": f["method"], "assumptions": f["assumptions"],
                "source_data": [b["id"] for b in estore.load().get("bills", [])],
                "bill_breakdown": f["bill_breakdown"]["lines"], "adjustments": f.get("adjustments")}
    err(422, "validation_error", "category must be 'water' or 'electricity'")


@router.get("/utilities/forecast")
def utilities_forecast(category: str = Query(...)):
    require_household()
    return forecast_for_ui(category)


# ---------------- what-if ----------------
class UIScenario(BaseModel):
    category: str
    reduction_percent: float | None = Field(default=None, gt=-100, lt=100)
    scenario: str | None = None
    params: dict = {}
    household_id: str | None = None


def run_scenario_for_ui(category, reduction_percent=None, scenario=None, params=None):
    """Routes to the engine that owns the calculation; returns the app's Scenario shape + full details."""
    params = params or {}
    if category == "water":
        from water import scenarios as wsc
        from water import store as wstore
        key, p = (scenario, params) if scenario else ("custom_change", {"pct": -float(reduction_percent or 0)})
        try:
            r = wsc.run(wstore.load(), key, p)
        except (KeyError, ValueError) as exc:
            err(422, "validation_error", str(exc).strip("'\""))
        if r["status"] != "ok":
            return {"baseline": None, "adjusted": None, "delta": None, "unit_change": None, "status": r["status"],
                    "message": r.get("message"), "assumptions": [m["prompt"] for m in r.get("missing", [])], "details": r}
        return {"baseline": r["baseline"]["rs"], "adjusted": r["with_scenario"]["rs"],
                "delta": round(r["baseline"]["rs"] - r["with_scenario"]["rs"], 2),
                "unit_change": round(-r["difference"]["m3"], 2), "unit": "m³", "status": "ok",
                "message": f"{r['title']}: {abs(r['difference']['litres']):,} L "
                           f"{'less' if r['difference']['litres'] < 0 else 'more'} in {r['period_start']} to "
                           f"{r['period_end']}; the CWA bill is recalculated.",
                "assumptions": [a["text"] for a in r["assumptions"]] + [r["calculation"], r["note"]], "details": r}
    if category == "electricity":
        from electricity import advice as eadvice
        from electricity import forecast as ef
        from electricity import store as estore
        from electricity import tariff as etariff
        s = estore.load()
        if scenario:
            try:
                r = eadvice.scenario(s, scenario, params)
            except (KeyError, ValueError) as exc:
                err(422, "validation_error", str(exc).strip("'\""))
            if r.get("status") != "ok":
                return {"baseline": None, "adjusted": None, "delta": None, "unit_change": None,
                        "status": r.get("status"), "message": r.get("message") or r.get("reason"),
                        "assumptions": [], "details": r}
            return {"baseline": r["baseline"]["cost_rs"], "adjusted": r["with_action"]["cost_rs"],
                    "delta": round(r["baseline"]["cost_rs"] - r["with_action"]["cost_rs"], 2),
                    "unit_change": round(-r["difference"]["kwh"], 2), "unit": "kWh", "status": "ok",
                    "message": f"{r['title']}: {abs(r['difference']['kwh']):g} kWh less in {r['period_start']} to "
                               f"{r['period_end']}; the CEB bill is recalculated.",
                    "assumptions": list(r.get("assumptions") or []) + [r.get("formula", "")], "details": r}
        f = ef.forecast(s)
        if f.get("status") != "ok":
            return {"baseline": None, "adjusted": None, "delta": None, "unit_change": None, "status": "needs_input",
                    "message": "Add a confirmed electricity bill first: this scenario starts from your measured use.",
                    "assumptions": [], "details": f}
        pct = float(reduction_percent or 0)
        base_kwh = f["kwh"]["mid"]
        new_kwh = base_kwh * (1 - pct / 100)
        prof = s.get("profile", {})
        code, tv = prof.get("ceb_tariff", "140"), prof.get("tv_licence", True)
        before = etariff.electricity_bill(base_kwh, code, tv).total
        after = etariff.electricity_bill(new_kwh, code, tv).total
        return {"baseline": before, "adjusted": after, "delta": round(before - after, 2),
                "unit_change": round(base_kwh - new_kwh, 2), "unit": "kWh", "status": "ok",
                "message": f"{pct:g}% less electricity: {base_kwh - new_kwh:.1f} kWh less in {f['period_start']} to "
                           f"{f['period_end']}; the whole CEB tariff {code} is recalculated.",
                "assumptions": [f"{pct:g}% less use than your estimate of {base_kwh:g} kWh",
                                "CEB rising blocks, minimum charge, meter rental" + (" and TV licence" if tv else ""),
                                "A plan is not a measured saving: your next bill will show the real change."],
                "details": {"baseline_kwh": base_kwh, "scenario_kwh": round(new_kwh, 2), "tariff_code": code}}
    err(422, "validation_error", "category must be 'water' or 'electricity'")


@router.post("/household/scenarios")
def household_scenarios(body: UIScenario):
    ctx, h = require_household()
    r = run_scenario_for_ui(body.category, body.reduction_percent, body.scenario, body.params)
    ctx.db.table("activity_logs").insert({"household_id": h["id"], "event_type": f"{body.category}.scenario_run",
                                          "details": {"module": body.category, "scenario": body.scenario or "percent",
                                                      "reduction_percent": body.reduction_percent,
                                                      "delta_rs": r.get("delta")}}).execute()
    return r


# ---------------- Big Brain ----------------
class ApplyIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    language: str = "en"


def _translate_fields(result, language):
    """French / Kreol: the suggestion and the 'applied' message are worded by Gemini in that language, kept only if
    every number stays exactly the same (same check as the coach answer). Without a key they stay in English."""
    if language not in ("fr", "mfe"):
        return result
    from big_brain import coach as C
    for field in ("suggestion", "applied_message"):
        if result.get(field):
            out = C.rephrase({"answer": result[field]}, language)
            if out.get("source") == "gemini":
                result[field] = out["answer"]
    return result


@router.post("/household/coach/apply")
def coach_apply(body: ApplyIn):
    """The Apply button under a what-if answer: recalculated on the server (client numbers are not trusted)."""
    from big_brain import whatif
    ctx, h = require_household()
    return _translate_fields(whatif.apply_plan(ctx, h, body.question), body.language)


@router.get("/household/plans")
def household_plans():
    from big_brain import whatif
    ctx, h = require_household()
    return whatif.list_plans(ctx, h)


@router.get("/household/dashboard")
def dashboard(explain: bool = True):
    from big_brain.service import build_dashboard
    ctx, h = require_household()
    return build_dashboard(ctx, h, use_ai=explain)


@router.get("/big-brain/dashboard")
def big_brain_dashboard(explain: bool = True):
    """Manvi's v3 endpoint (same path and JSON as her notebook), on this household's own data."""
    from big_brain.v3 import big_brain_v3
    ctx, h = require_household()
    return big_brain_v3(ctx, h, use_ai=explain)


@router.get("/household/insights")
def insights(explain: bool = True):
    from big_brain.service import build_dashboard, insights_for_ui
    from big_brain.v3 import big_brain_v3
    ctx, h = require_household()
    out = insights_for_ui(build_dashboard(ctx, h, use_ai=explain))
    v3 = big_brain_v3(ctx, h, use_ai=explain)["dashboard"]
    out["big_brain_summary"] = v3["summary"]                      # Manvi v3: one-paragraph plan for Home
    out["savings_30d"] = [{k: r.get(k) for k in ("rank", "module", "action_id", "title", "normalized_savings_30d_mur",
                                                 "estimated_savings_mur", "savings_period", "ai_explanation")}
                          for r in v3["recommendations"]]
    return out


class CoachIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    language: str = "en"
    household_id: str | None = None


@router.post("/household/coach")
def coach(body: CoachIn):
    """AI Coach (14 Nov): what-if questions about the bills and the budget, calculated by the module engines."""
    from big_brain import coach as C
    from big_brain import whatif
    ctx, h = require_household()
    if whatif.wants_apply(body.message):                 # "apply it", "do it": rule-based, applied straight away
        result = whatif.apply_plan(ctx, h, body.message)
    else:
        result = whatif.answer(h, body.message)
    result = C.rephrase(result, body.language)
    result = _translate_fields(result, body.language)
    ctx.db.table("activity_logs").insert({"household_id": h["id"], "event_type": "coach.question",
                                          "details": {"module": "big_brain", "intent": result["intent"], "question": body.message[:200],
                                                      "source": result["source"]}}).execute()
    return result


# ---------------- activity ----------------
SECURITY_LABELS = {
    "coach.question": lambda d: f"Asked the AI coach: {d.get('question')}" if d.get("question") else "Asked the AI coach",
    "pattern_set": "Security pattern set", "pattern_changed": "Security pattern changed",
    "pattern_ok": "Pattern accepted to {what}", "pattern_failed": "Wrong pattern while trying to {what}",
    "pattern_locked": "Pattern locked for 5 minutes after 5 wrong tries ({what})",
    "blocked": "BLOCKED: someone tried to {what} without the pattern", "allowed": "Allowed: {what}",
    "authenticator_on": "Microsoft Authenticator switched on", "authenticator_off": "Microsoft Authenticator switched off",
    "code_failed": "Wrong authenticator code", "code_locked": "Authenticator codes locked for 5 minutes",
    "password_failed": "Wrong password in a security check", "recovery_code_used": "A recovery code was used",
    "login_with_authenticator": "Logged in with Microsoft Authenticator",
    "account_reset": "Account reset (restorable for 24 hours)", "account_restored": "Account restored after a reset",
}


def _category(ev, d):
    """Activity tab sections: ai, water, electricity, groceries, security, household."""
    head = ev.split(".")[0]
    if head in ("water", "electricity", "security", "ai"):
        return head
    if head == "coach" or (d or {}).get("module") == "big_brain":
        return "ai"
    if head in ("receipt_confirmed", "recipe_cooked", "pantry_updated", "pantry_added", "recipe_saved") or \
            any(w in ev for w in ("receipt", "pantry", "recipe", "cook")):
        return "groceries"
    return (d or {}).get("module") if (d or {}).get("module") in ("water", "electricity", "groceries") else "household"


def _security_label(ev, d):
    from core.security import SENSITIVE
    what = SENSITIVE.get(d.get("action"), "do a protected action")
    return "Security · " + SECURITY_LABELS.get(ev.split(".", 1)[1], ev).format(what=what)


LABELS = {
    "ai.plan_applied": lambda d: f"Plan applied from the AI coach: {d.get('question')}",
    "receipt_confirmed": lambda d: f"Confirmed grocery purchase (Rs {d.get('total', 0):,.2f})" if d.get("total") is not None
    else "Confirmed grocery purchase",
    "recipe_cooked": lambda d: f"Cooked {d.get('recipe_name', 'a recipe')}; pantry stock reduced (no new expense)",
    "manual_add": lambda d: f"{d.get('name', 'Item')} added to the pantry ({d.get('quantity')} {d.get('unit')})",
    "manual_correction": lambda d: f"{d.get('name', 'Item')} corrected in the pantry",
    "marked_unavailable": lambda d: f"{d.get('name', 'Item')} marked unavailable",
    "marked_available": lambda d: f"{d.get('name', 'Item')} available again",
    "household_created": lambda d: "Household assessment saved",
    "household_updated": lambda d: "Household details updated",
    "water.bill_confirmed": lambda d: f"Water bill saved ({d.get('m3')} m³, {d.get('start')} to {d.get('end')})",
    "water.bill_replaced": lambda d: f"Water bill corrected ({d.get('m3')} m³)",
    "water.forecast_issued": lambda d: f"Water estimate saved for checking: {d.get('m3')} m³ from {d.get('period_start')}",
    "water.forecast_checked": lambda d: f"Water bill compared with our estimate (error {d.get('error_pct')}%)",
    "water.assessment_answered": lambda d: f"Water questions answered (version {d.get('version')})",
    "water.scenario_run": lambda d: f"Water what-if tried ({d.get('scenario')})",
    "water.scenario_saved_as_goal": lambda d: f"Water goal saved ({d.get('scenario')})",
    "water.action_completed": lambda d: f"Water goal completed ({d.get('scenario')})",
    "water.reading_added": lambda d: f"Water meter reading added ({d.get('index_m3')} m³ on {d.get('date')})",
    "electricity.bill_added": lambda d: f"Electricity bill saved ({d.get('kwh')} kWh, {d.get('start')} to {d.get('end')})",
    "electricity.assessment_updated": lambda d: "Electricity questions answered",
    "electricity.scenario_run": lambda d: "Electricity what-if tried",
    "electricity.action_selected": lambda d: f"Electricity goal saved ({d.get('action')})",
    "electricity.action_completed": lambda d: f"Electricity goal completed ({d.get('action')})",
    "electricity.reading_added": lambda d: f"Electricity meter reading added ({d.get('index_kwh')} kWh)",
    "coach.question": lambda d: f"AI coach answered a {d.get('intent', '')} question",
}


@router.get("/activity")
def activity(limit: int = 100):
    ctx, h = require_household()
    rows = (ctx.db.table("activity_logs").select("id,event_type,details,created_at,related_entity_id")
            .eq("household_id", h["id"]).order("created_at", desc=True).limit(max(1, min(limit, 500))).execute().data or [])
    out = []
    for r in rows:
        d = r.get("details") or {}
        ev = r["event_type"]
        try:
            msg = (_security_label(ev, d) if ev.startswith("security.") else
                   LABELS[ev](d) if ev in LABELS else ev.replace(".", ": ").replace("_", " ").capitalize())
        except Exception:
            msg = ev
        out.append({"id": r["id"], "at": r["created_at"], "message": msg, "category": _category(ev, d),
                    "kind": d.get("module") or ev.split(".")[0].split("_")[0], "event_type": ev, "details": d})
    return out


# ---------------- demo helpers ----------------
@router.post("/demo/sample")
def demo_sample():
    """Load the clearly labelled sample household: fictional water bills, the team's real CEB bill history,
    a fictional receipt (pantry) and expiry dates. For rehearsing the demo."""
    ctx = require_context()
    from electricity import store as estore0
    from water import store as wstore0
    if household(ctx) is not None and (wstore0.load().get("bills") or estore0.load().get("bills")):
        err(409, "has_data", "This account already has bills. Use Settings -> Reset account first (pattern needed).")
    if household(ctx) is None:
        onboarding(Onboarding(name="Sample household (fictional)", members=4, home_type="House", monthly_target=15000,
                              electricity_tariff="140", main_goal="reduce_expenses", region="Centre"))
    from electricity import store as estore
    from water import store as wstore
    w = wstore.reset(sample=True)
    w["today"] = None
    wstore.save(w)
    e = estore.reset(sample=True)
    e["today"] = None
    e["assessment"] = {"E1": ["air_conditioner", "water_heater", "washing_machine"], "E2": "4_8", "E3": "electric",
                       "E4": "gas", "E5": "no"}
    estore.save(e)
    h = household(ctx)
    ctx.db.rpc("confirm_grocery_receipt", {
        "p_household_id": h["id"], "p_source_identifier": "sample-receipt-001", "p_retailer": "Sample shop (fictional)",
        "p_receipt_date": date.today().isoformat(), "p_total": 238,
        "p_items": [{"original_name": "Riz 1kg", "normalized_name": "rice", "quantity": 1, "unit": "kg", "line_total": 95},
                    {"original_name": "Carottes", "normalized_name": "carrot", "quantity": 2, "unit": "piece", "line_total": 28},
                    {"original_name": "Petits pois 500g", "normalized_name": "peas", "quantity": 0.5, "unit": "kg", "line_total": 70},
                    {"original_name": "Oignons", "normalized_name": "onion", "quantity": 3, "unit": "piece", "line_total": 45}]}).execute()
    return {"ok": True, "note": "Sample household loaded. Water bills are fictional; electricity bills are the team's "
                                "real CEB history; the receipt is fictional."}


@router.post("/demo/reset")
def demo_reset(x_step_up: str | None = Header(default=None)):
    """Same as POST /account/reset (pattern needed, undoable for 24 hours)."""
    from integration.security_routes import reset_account
    return reset_account(x_step_up)
