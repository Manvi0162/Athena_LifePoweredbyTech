"""What-if scenarios: visible formulas, stated assumptions, and an honest "not enough data" answer.

Every scenario declares what it NEEDS (assessment answers, household size, a confirmed bill, or a value only the
user can give). If something is missing it returns status "needs_input" with the question to answer, never a guess.
A scenario never changes bills, readings or saved forecasts: it is compared against the forecast, side by side.
Rupees are always the whole CWA tariff recalculated (baseline vs scenario), never m3 x an average price.

Default values (user can change them; marked "estimated" in every answer):
  shower 7.9 L/min, toilet flush 9.8 L, washing machine 111 L/load: REU 2016 averages (Water Research Foundation)
  dripping tap 31 L/day: US EPA WaterSense (1 drip/second > 3,000 gallons a year)
"""
import uuid

from . import assessment as A
from .forecast import bills, forecast, next_cycle

SHOWER_FLOW_L_MIN = 7.9
FLUSH_L = 9.8
WASHER_L_PER_LOAD = 111
DRIP_L_DAY = 31
NOTE = "A plan is not a measured saving: only a later bill or meter reading can show the real change."

CATALOGUE = {
    "shorter_showers": {
        "title": "Shorter showers", "type": "per_day", "direction": "less",
        "params": {"minutes_less": {"default": 2, "range": [0.5, 30]},
                   "flow_l_per_min": {"default": SHOWER_FLOW_L_MIN, "range": [2, 30], "estimated": True}},
        "needs": ["members", "W1_shower_minutes"],
        "formula": "people x minutes_less x flow_l_per_min"},
    "extra_showers": {
        "title": "More showers (e.g. hot season)", "type": "per_day", "direction": "more",
        "params": {"extra_showers_per_day": {"default": None, "range": [0.5, 40], "required": True,
                                             "ask": "How many extra showers per day for the whole household?"},
                   "flow_l_per_min": {"default": SHOWER_FLOW_L_MIN, "range": [2, 30], "estimated": True}},
        "needs": ["W1_shower_minutes"],
        "formula": "extra_showers_per_day x shower minutes (W1) x flow_l_per_min"},
    "greywater_flush": {
        "title": "Flush with reused washing water", "type": "per_day", "direction": "less",
        "params": {"flushes_replaced_per_day": {"default": None, "range": [0.5, 200]},
                   "litres_per_flush": {"default": FLUSH_L, "range": [2, 20], "estimated": True}},
        "needs": ["members", "W2_flushes_per_person"],
        "formula": "flushes_replaced_per_day x litres_per_flush"},
    "full_laundry_loads": {
        "title": "Only run full laundry loads", "type": "per_day", "direction": "less",
        "params": {"loads_less_per_week": {"default": 1, "range": [0.5, 21]},
                   "litres_per_load": {"default": WASHER_L_PER_LOAD, "range": [10, 250], "estimated": True}},
        "needs": ["W3_laundry_loads_per_week"],
        "formula": "loads_less_per_week x litres_per_load / 7"},
    "fix_dripping_tap": {
        "title": "Fix a dripping tap", "type": "per_day", "direction": "less",
        "params": {"taps": {"default": 1, "range": [1, 20]},
                   "litres_per_day": {"default": DRIP_L_DAY, "range": [1, 500], "estimated": True}},
        "needs": [],
        "formula": "taps x litres_per_day"},
    "less_outdoor_water": {
        "title": "Less garden / car / outdoor water", "type": "per_day", "direction": "less",
        "params": {"sessions_less_per_week": {"default": 1, "range": [0.5, 14]},
                   "litres_per_session": {"default": None, "range": [1, 2000], "required": True,
                                          "ask": "How many litres does one session use? Time how long your hose "
                                                 "fills a 10 L bucket, then: 10 / seconds x 60 x minutes of use."}},
        "needs": ["W4_outdoor_use"],
        "formula": "sessions_less_per_week x litres_per_session / 7"},
    "guests_or_away": {
        "title": "Guests staying / someone away", "type": "period", "direction": "either",
        "params": {"people_change": {"default": None, "range": [-30, 50], "required": True,
                                     "ask": "How many people more (e.g. 2) or fewer (e.g. -1)?"},
                   "days": {"default": None, "range": [1, 35], "required": True, "ask": "For how many days?"}},
        "needs": ["members", "bill"],
        "formula": "(your m3 per day / people) x people_change x days"},
    "custom_change": {
        "title": "My own change (%)", "type": "period", "direction": "either",
        "params": {"pct": {"default": None, "range": [-90, 200], "required": True,
                           "ask": "By how many % will usage change (e.g. 10 or -15)?"}},
        "needs": ["bill"],
        "formula": "forecast m3 x pct / 100"},
}

NEEDS_PROMPT = {
    "members": "Answer the general question: how many people live in your household?",
    "bill": "Add a confirmed CWA bill first: this scenario is based on your measured use.",
    **{k: f"Answer water question {k[:2]}: {A.QUESTIONS[k]['question']}" for k in A.QUESTIONS},
}


def _missing(state, key):
    spec, out = CATALOGUE[key], []
    for need in spec["needs"]:
        if need == "members" and not state.get("household", {}).get("members"):
            out.append({"item": "members", "prompt": NEEDS_PROMPT["members"]})
        elif need == "bill" and not bills(state):
            out.append({"item": "bill", "prompt": NEEDS_PROMPT["bill"]})
        elif need in A.QUESTIONS and not A.known(state, need):
            out.append({"item": need, "prompt": NEEDS_PROMPT[need] + " ('Not sure' is not enough for this scenario.)"})
    if key == "less_outdoor_water" and A.value(state, "W4_outdoor_use") == 0:
        out.append({"item": "W4_outdoor_use", "prompt": "You told us you never use water outdoors, so there is nothing to reduce."})
    return out


def resolve(state, key, params):
    """Check parameters. Returns (values, assumptions, missing)."""
    if key not in CATALOGUE:
        raise KeyError(f"Unknown scenario '{key}'. Choose one of: {', '.join(CATALOGUE)}")
    spec = CATALOGUE[key]
    params = {k: v for k, v in (params or {}).items() if v is not None}
    unknown = set(params) - set(spec["params"])
    if unknown:
        raise ValueError(f"'{key}' does not take {', '.join(sorted(unknown))}. It takes: {', '.join(spec['params'])}")
    members = state.get("household", {}).get("members")
    vals, assumptions, missing = {}, [], []
    for name, p in spec["params"].items():
        if name in params:
            try:
                v = float(params[name])
            except (TypeError, ValueError):
                raise ValueError(f"{name} must be a number")
            lo, hi = p["range"]
            if not lo <= v <= hi:
                raise ValueError(f"{name} must be between {lo:g} and {hi:g} (got {v:g})")
            vals[name] = v
            assumptions.append({"text": f"{name} = {v:g}", "kind": "user_given"})
        elif p.get("required"):
            missing.append({"item": name, "prompt": p["ask"]})
        elif p["default"] is not None:
            vals[name] = float(p["default"])
            assumptions.append({"text": f"{name} = {p['default']:g}", "kind": "estimated" if p.get("estimated") else "default"})
    # defaults that come from the assessment answers
    if key == "greywater_flush" and "flushes_replaced_per_day" not in vals and members:
        vals["flushes_replaced_per_day"] = float(members)
        assumptions.append({"text": f"flushes_replaced_per_day = {members} (one per person)", "kind": "default"})
    if key in ("shorter_showers", "extra_showers") and A.known(state, "W1_shower_minutes"):
        vals["usual_minutes"] = A.value(state, "W1_shower_minutes")
        assumptions.append({"text": f"usual shower {vals['usual_minutes']:g} min (middle of your answer "
                                    f"'{A.latest(state)['answers']['W1_shower_minutes']}')", "kind": "from_answer"})
        if key == "shorter_showers" and vals["minutes_less"] >= vals["usual_minutes"]:
            raise ValueError(f"minutes_less ({vals['minutes_less']:g}) must be shorter than your usual shower "
                             f"({vals['usual_minutes']:g} min)")
    if key == "greywater_flush" and A.known(state, "W2_flushes_per_person") and members:
        total = A.value(state, "W2_flushes_per_person") * members
        if vals.get("flushes_replaced_per_day", 0) > total:
            raise ValueError(f"You flush about {total:g} times a day in total, so you cannot replace "
                             f"{vals['flushes_replaced_per_day']:g}")
    if key == "full_laundry_loads" and A.known(state, "W3_laundry_loads_per_week"):
        loads = A.value(state, "W3_laundry_loads_per_week")
        if vals["loads_less_per_week"] > loads:
            raise ValueError(f"You wash about {loads:g} loads a week, so you cannot run {vals['loads_less_per_week']:g} fewer")
    if key == "less_outdoor_water" and A.known(state, "W4_outdoor_use"):
        sessions = A.value(state, "W4_outdoor_use")
        if sessions and vals["sessions_less_per_week"] > sessions:
            raise ValueError(f"You use water outdoors about {sessions:g} times a week, so you cannot cut "
                             f"{vals['sessions_less_per_week']:g}")
    return vals, assumptions, _missing(state, key) + missing


def litres_per_day(state, key, v):
    """Change in litres per day (negative = less water), with the formula filled in."""
    members = state.get("household", {}).get("members") or 0
    if key == "shorter_showers":
        return -v["minutes_less"] * v["flow_l_per_min"] * members, \
            f"{members} people x {v['minutes_less']:g} min x {v['flow_l_per_min']:g} L/min"
    if key == "extra_showers":
        return v["extra_showers_per_day"] * v["usual_minutes"] * v["flow_l_per_min"], \
            f"{v['extra_showers_per_day']:g} showers x {v['usual_minutes']:g} min x {v['flow_l_per_min']:g} L/min"
    if key == "greywater_flush":
        return -v["flushes_replaced_per_day"] * v["litres_per_flush"], \
            f"{v['flushes_replaced_per_day']:g} flushes x {v['litres_per_flush']:g} L"
    if key == "full_laundry_loads":
        return -v["loads_less_per_week"] * v["litres_per_load"] / 7, \
            f"{v['loads_less_per_week']:g} loads x {v['litres_per_load']:g} L / 7 days"
    if key == "fix_dripping_tap":
        return -v["taps"] * v["litres_per_day"], f"{v['taps']:g} tap(s) x {v['litres_per_day']:g} L/day"
    if key == "less_outdoor_water":
        return -v["sessions_less_per_week"] * v["litres_per_session"] / 7, \
            f"{v['sessions_less_per_week']:g} sessions x {v['litres_per_session']:g} L / 7 days"
    raise KeyError(key)


def saving_per_day(state, key, params):
    """m3 per day saved by a completed per-day action (positive = saving), or None for period scenarios."""
    if key not in CATALOGUE or CATALOGUE[key]["type"] != "per_day":
        return None
    try:
        v, _, missing = resolve(state, key, params)
    except ValueError:
        return None
    if missing:
        return None
    return -litres_per_day(state, key, v)[0] / 1000


def run(state, key, params=None):
    spec = CATALOGUE[key] if key in CATALOGUE else None
    v, assumptions, missing = resolve(state, key, params)
    rid = uuid.uuid4().hex[:8]
    head = {"id": rid, "scenario": key, "title": spec["title"], "params": params or {}, "note": NOTE}
    if missing:
        return {**head, "status": "needs_input", "missing": missing,
                "message": "Not enough data for this scenario yet. " + " ".join(m["prompt"] for m in missing)}
    base = forecast(state)
    start, n_days = next_cycle(state)
    if spec["type"] == "per_day":
        lpd, formula = litres_per_day(state, key, v)
        delta_m3 = lpd * n_days / 1000
        formula_full = f"{formula} = {lpd:+.1f} L/day; x {n_days} days = {delta_m3 * 1000:+,.0f} L"
    elif key == "guests_or_away":
        members = state["household"]["members"]
        rate = base["observed_vs_assumed"]["observed_m3_per_day"]
        days = min(v["days"], n_days)
        delta_m3 = rate / members * v["people_change"] * days
        lpd = delta_m3 * 1000 / n_days
        formula_full = (f"({rate * 1000:.0f} L/day / {members} people) x {v['people_change']:+g} people x {days:g} days "
                        f"= {delta_m3 * 1000:+,.0f} L")
    else:
        delta_m3 = base["estimated_units"] * v["pct"] / 100
        lpd = delta_m3 * 1000 / n_days
        formula_full = f"{base['estimated_units']:g} m3 x {v['pct']:+g}% = {delta_m3:+.2f} m3"
    out = {**head, "status": "ok", "type": spec["type"], "formula": spec["formula"], "calculation": formula_full,
           "change_litres_per_day": round(lpd, 1), "assumptions": assumptions}
    if base["estimated_units"] is None:
        return {**out, "status": "partial", "difference": {"litres": round(delta_m3 * 1000), "m3": round(delta_m3, 3),
                                                            "period_days": n_days},
                "message": "Litres only: add a confirmed CWA bill to see your forecast and the rupee effect."}
    new = forecast(state, extra_m3=delta_m3)
    return {**out, "period_start": base["period_start"], "period_end": base["period_end"],
            "baseline": {"m3": base["estimated_units"], "rs": base["cost"]["rs"], "status": base["status"]},
            "with_scenario": {"m3": new["estimated_units"], "rs": new["cost"]["rs"]},
            "difference": {"m3": round(new["estimated_units"] - base["estimated_units"], 2),
                           "litres": round((new["estimated_units"] - base["estimated_units"]) * 1000),
                           "rs": round(new["cost"]["rs"] - base["cost"]["rs"], 2)},
            "cost_how": "whole CWA tariff recalculated for baseline and scenario",
            "limits": "Below Rs 45 of water charges the minimum charge applies, so small changes may show Rs 0."}
