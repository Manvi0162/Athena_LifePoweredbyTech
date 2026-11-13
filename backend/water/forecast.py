"""Water forecast: honest, evidence-based, rebuilt from the saved records every time.

NEXT BILLING CYCLE (default)
  1. Observed baseline : m3 per day from the confirmed bills (cycle length removed) x days in the next cycle.
                         Example: 18 m3 / 30 days = 600 L/day; x 31 days = 18.6 m3.
  2. Season            : hotter / cooler than the months of those bills (data: Singapore study + Mauritian
                         temperatures, see seasonality.py). Shown as its own line.
  3. Expected change   : the user's answer to W5 ("increase about 10%"), only if they gave a size. Own line.
  4. Completed actions : savings of actions completed after the last bill. Own line.
  5. Correction        : after 2+ checked forecasts (bill vs prediction), the median actual/predicted ratio,
                         if it is 3% or more off. Own line.
  cost = CWA tariff on the result (never a flat price). Range from bill-to-bill variation (3+ bills) or from
  real day-to-day variation (fewer bills).
CURRENT CYCLE: only with dated meter readings (never claimed from bills alone).
STATUS: insufficient_data (no measured usage) -> preliminary (1-2 bills) -> better_supported (3+ bills and
  2+ checked forecasts). DATA COMPLETENESS and RELIABILITY are separate: answering questions raises completeness,
  only measured evidence raises reliability.
"""
import random
import statistics
import uuid
from datetime import date, datetime, timedelta, timezone

from . import assessment as A
from . import seasonality as S
from . import tariff

TARIFF_VERSION = "CWA domestic tariff 2012 (unchanged in 2026)"
DEFAULT_CYCLE = 30
CORRECTION_MIN_CHECKS = 2
CORRECTION_THRESHOLD = 0.03

MESSAGES = {
    "insufficient_data": "Add your first bill or meter reading to receive a household-specific estimate.",
    "preliminary": "This is an early estimate based on {n} billing period{s}. Your future usage may differ.",
    "better_supported": "Based on {n} bills and {c} checks of earlier estimates against real bills.",
    "assessment_prompt": "Tell us about your habits to personalise this forecast and identify possible savings.",
    "after_assessment": "Your habits are now included in personalised insights. More actual readings will help us "
                        "evaluate forecast reliability.",
}


def d(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


def today(state):
    return d(state.get("today") or date.today())


def bills(state):
    return sorted(state.get("bills", []), key=lambda b: b["start"])


def days_of(b):
    return (d(b["end"]) - d(b["start"])).days


def _span(start, n):
    return [start + timedelta(i) for i in range(n)]


def shape(day, profile):
    return S.weekday_factor(day) * S.season_factor(day, profile)


def usual_day(bill_list, profile):
    """m3 on an 'average' day with weekends and season removed, from the given bills."""
    m3 = sum(float(b["m3"]) for b in bill_list)
    weight = sum(shape(x, profile) for b in bill_list for x in _span(d(b["start"]), days_of(b)))
    return m3 / weight if weight else 0.0


def core(bill_list, profile, start, n_days):
    """Observed baseline and season-adjusted m3 for n_days from start, using only bill_list (no other inputs)."""
    basis = bill_list[-3:]
    plain_rate = sum(float(b["m3"]) for b in basis) / sum(days_of(b) for b in basis)
    usual = usual_day(basis, profile)
    days = _span(start, n_days)
    with_season = usual * sum(shape(x, profile) for x in days)
    return {"basis": basis, "plain_rate": plain_rate, "usual": usual, "baseline": plain_rate * n_days,
            "with_season": with_season}


def next_cycle(state):
    bl = bills(state)
    n = round(statistics.mean(days_of(b) for b in bl[-3:])) if bl else DEFAULT_CYCLE
    n = min(max(n, 25), 35)
    start = d(bl[-1]["end"]) if bl else today(state)
    return start, n


# ---------- bill vs prediction ----------
def backtests(state):
    """Predict each bill from the bills before it with the same method (genuine out-of-sample checks)."""
    profile, bl, out = state.get("profile", {}), bills(state), []
    for k in range(1, len(bl)):
        c = core(bl[:k], profile, d(bl[k]["start"]), days_of(bl[k]))
        actual = float(bl[k]["m3"])
        out.append({"kind": "backtest", "bill_id": bl[k]["id"], "period_start": bl[k]["start"], "period_end": bl[k]["end"],
                    "predicted_m3": round(c["with_season"], 2), "actual_m3": actual,
                    "error_m3": round(c["with_season"] - actual, 2),
                    "error_pct": round((c["with_season"] - actual) / actual * 100, 1) if actual else None,
                    "note": f"Predicted from the {k} earlier bill{'s' if k > 1 else ''} only"})
    return out


def all_checks(state):
    return state.get("checks", []) + backtests(state)


def check_against_forecast(state, bill):
    """Called when a bill is confirmed: compare it with the latest saved forecast for that period."""
    snaps = [f for f in state.get("forecasts", []) if f.get("estimated_units") is not None]
    best, best_overlap = None, 0
    for f in snaps:
        lo = max(d(f["period_start"]), d(bill["start"]))
        hi = min(d(f["period_end"]), d(bill["end"]))
        overlap = (hi - lo).days
        if overlap > best_overlap:
            best, best_overlap = f, overlap
    if not best or best_overlap < 0.5 * days_of(bill):
        return None
    f_days = (d(best["period_end"]) - d(best["period_start"])).days
    predicted = best["estimated_units"] / f_days * days_of(bill)          # same length as the bill
    actual = float(bill["m3"])
    sewer = state.get("profile", {}).get("sewer", False)
    chk = {"kind": "real", "id": uuid.uuid4().hex[:8], "forecast_id": best["id"], "bill_id": bill["id"],
           "period_start": bill["start"], "period_end": bill["end"],
           "predicted_m3": round(predicted, 2), "actual_m3": actual, "error_m3": round(predicted - actual, 2),
           "error_pct": round((predicted - actual) / actual * 100, 1) if actual else None,
           "predicted_rs": tariff.water_bill(predicted, sewer).total, "actual_rs": tariff.water_bill(actual, sewer).total,
           "forecast_status": best["status"]}
    state.setdefault("checks", []).append(chk)
    return chk


def correction(state):
    ratios = [c["actual_m3"] / c["predicted_m3"] for c in all_checks(state) if c["predicted_m3"]][-4:]
    if len(ratios) < CORRECTION_MIN_CHECKS:
        return None
    r = statistics.median(ratios)
    return r if abs(r - 1) >= CORRECTION_THRESHOLD else None


def reliability(state):
    checks = all_checks(state)
    errs = [abs(c["error_pct"]) for c in checks if c["error_pct"] is not None]
    return {"checked_forecasts": sum(1 for c in checks if c["kind"] == "real"),
            "backtests": sum(1 for c in checks if c["kind"] == "backtest"),
            "mean_abs_error_pct": round(statistics.mean(errs), 1) if errs else None,
            "latest": checks[-3:]}


# ---------- completeness ----------
def completeness(state):
    bl = bills(state)
    last = bl[-1] if bl else {}
    items = [
        ("household_size", bool(state.get("household", {}).get("members")), "Answer the general question: people in your household."),
        ("confirmed_bill", bool(bl), "Add your first CWA bill (photo or typed in)."),
        ("bill_amount", last.get("amount_rs") is not None, "Add the amount on your latest bill so we can check it against the tariff."),
        ("bill_meter_readings", last.get("end_reading") is not None, "Add the meter readings printed on your latest bill."),
        ("sewer_known", state.get("profile", {}).get("sewer") is not None, "Tell us if your home is connected to the public sewer."),
        ("reading_this_cycle", any(r["date"] > last.get("end", "") for r in state.get("readings", [])),
         "Add a meter reading this month for a current-month estimate."),
    ] + [(k, A.known(state, k), f"Answer: {A.QUESTIONS[k]['question']}") for k in A.QUESTIONS]
    done = sum(1 for _, ok, _ in items if ok)
    return {"pct": round(done / len(items) * 100), "done": done, "total": len(items),
            "missing": [{"item": k, "prompt": p} for k, ok, p in items if not ok]}


# ---------- main forecast ----------
def status_of(state):
    n = len(bills(state))
    if n == 0:
        return "insufficient_data"
    if n >= 3 and len(all_checks(state)) >= 2:
        return "better_supported"
    return "preliminary"


def completed_action_saving(state, start, n_days):
    """m3 saved in the period by actions completed AFTER the last bill (earlier ones are inside the bills)."""
    from .scenarios import saving_per_day
    bl = bills(state)
    last_end = d(bl[-1]["end"]) if bl else date.min
    out, ids = 0.0, []
    for a in state.get("actions", []):
        if a["status"] != "completed" or d(a["completed_on"]) < last_end:
            continue
        per_day = saving_per_day(state, a["key"], a.get("params", {}))
        if per_day is None:
            continue
        days = sum(1 for x in _span(start, n_days) if x >= d(a["completed_on"]))
        out += per_day * days
        ids.append(a["id"])
    return out, ids


def forecast(state, extra_m3=0.0):
    """Next billing cycle. extra_m3 (negative = saving) is used by what-if scenarios only."""
    st = status_of(state)
    comp = completeness(state)
    base = {"kind": "water", "module": "water", "units": "m3", "currency": "MUR", "status": st,
            "data_completeness": comp, "assessment_complete": A.complete(state),
            "assessment_version": A.latest(state)["version"], "reliability": reliability(state)}
    if st == "insufficient_data":
        return {**base, "status_message": MESSAGES["insufficient_data"], "estimated_units": None, "cost": None,
                "period": None, "method": None, "source_bill_count": 0, "source_ids": [],
                "prompts": [m["prompt"] for m in comp["missing"][:3]]}
    profile = state.get("profile", {})
    start, n_days = next_cycle(state)
    end = start + timedelta(n_days)
    c = core(bills(state), profile, start, n_days)
    lines = [{"label": f"Same daily use as your bills: {c['plain_rate'] * 1000:.0f} L/day x {n_days} days",
              "m3": round(c["baseline"], 3), "kind": "observed",
              "source": f"{len(c['basis'])} confirmed bill(s): " + ", ".join(b["id"] for b in c["basis"])}]
    season = c["with_season"] - c["baseline"]
    lines.append({"label": "Season: hotter months use more water" if season >= 0 else "Season: cooler months use less water",
                  "m3": round(season, 3), "kind": "data_adjustment",
                  "source": f"+{S.slope(profile) * 100:.1f}% per degC (Salvo 2018) and Mauritian monthly temperatures"})
    total = c["with_season"]
    adjustments = []
    w5 = A.latest(state)["answers"]
    direction = A.value(state, "W5_expected_change")
    if direction and w5.get("W5_change_pct"):
        m3 = total * direction * w5["W5_change_pct"] / 100
        adjustments.append({"label": f"You expect usage to {'increase' if direction > 0 else 'decrease'} by about "
                                     f"{w5['W5_change_pct']:g}%" + (f" ({w5['W5_reason']})" if w5.get("W5_reason") else ""),
                            "m3": round(m3, 3), "kind": "user_declared", "source": f"assessment v{A.latest(state)['version']}, W5"})
        total += m3
    saved, action_ids = completed_action_saving(state, start, n_days)
    if saved:
        adjustments.append({"label": "Actions you completed", "m3": round(-saved, 3), "kind": "action",
                            "source": "actions " + ", ".join(action_ids)})
        total -= saved
    r = correction(state)
    if r:
        m3 = total * (r - 1)
        adjustments.append({"label": f"Correction from past estimates: we were {abs(1 - 1 / r) * 100:.0f}% too "
                                     f"{'low' if r > 1 else 'high'}", "m3": round(m3, 3), "kind": "correction",
                            "source": "bill vs prediction checks"})
        total += m3
    if extra_m3:
        adjustments.append({"label": "What-if scenario", "m3": round(extra_m3, 3), "kind": "scenario", "source": "scenario"})
        total += extra_m3
    total = max(total, 0.0)
    lo_r, hi_r = _range(state, c, profile, start, n_days)
    est = {"low": round(total * lo_r, 2), "mid": round(total, 2), "high": round(total * hi_r, 2)}
    sewer = profile.get("sewer", False)
    bill_mid = tariff.water_bill(est["mid"], sewer)
    n_b, n_chk = len(bills(state)), len(all_checks(state))
    msg = MESSAGES[st].format(n=n_b, s="" if n_b == 1 else "s", c=n_chk)
    prompts = [] if A.complete(state) else [MESSAGES["assessment_prompt"]]
    if direction and not w5.get("W5_change_pct"):
        prompts.append("You said your usage will change next month: tell us roughly by how much (%) to include it.")
    bill_ids = [b["id"] for b in bills(state)]
    return {
        **base, "status_message": msg, "prompts": prompts,
        "period": f"next_{n_days}_day_cycle", "period_start": start.isoformat(), "period_end": end.isoformat(),
        "estimated_units": est["mid"], "range": {"low": est["low"], "high": est["high"]},
        "lines": lines + adjustments, "adjustments": adjustments,
        "method": "historical_daily_baseline",
        "method_explained": "m3 per day from your confirmed bills x days in the next cycle; season, your declared "
                            "changes, completed actions and past-error correction shown as separate lines; cost from "
                            "the CWA tariff",
        "source_bill_count": n_b, "source_ids": bill_ids + action_ids + ([f"assessment_v{A.latest(state)['version']}"] if A.latest(state)["version"] else []),
        "assumptions": ["unchanged use apart from the lines shown", f"{n_days}-day period",
                        "Mauritian defaults: roof tank, no bucket baths, car wash about once a month, no water cuts"],
        "observed_vs_assumed": {"observed_m3_per_day": round(c["plain_rate"], 4),
                                "assumed": [l["label"] for l in lines[1:] + adjustments]},
        "cost": {"rs": bill_mid.total, "low_rs": tariff.water_bill(est["low"], sewer).total,
                 "high_rs": tariff.water_bill(est["high"], sewer).total,
                 "how": "CWA rising blocks + minimum charge + meter rent + postal" + (" + wastewater" if sewer else ""),
                 "tariff_version": TARIFF_VERSION, "breakdown": bill_mid.as_dict()["lines"],
                 "note": "tariff_calculated_only: not a bill amount from CWA"},
        "block": tariff.next_block(est["mid"]),
        "season": S.explain(profile, sorted({x.month for x in _span(start, n_days)})),
    }


def _range(state, c, profile, start, n_days):
    bl = bills(state)
    if len(bl) >= 3:
        ratios = [usual_day([b], profile) / c["usual"] for b in bl[-6:] if c["usual"]]
        return min(min(ratios), 0.97), max(max(ratios), 1.03)
    rnd = random.Random(f"{state.get('seed', 'water')}-range")
    days = _span(start, n_days)
    expected = sum(shape(x, profile) for x in days)
    sims = sorted(sum(shape(x, profile) * S.random_day(rnd) for x in days) / expected for _ in range(400))
    spread = 1.5 if len(bl) == 1 else 1.0          # one bill: we cannot see month-to-month variation, so widen
    return 1 - (1 - sims[40]) * spread, 1 + (sims[360] - 1) * spread


def snapshot(state, reason):
    """Freeze the current forecast (so a later bill can be compared with what we said)."""
    f = forecast(state)
    if f["estimated_units"] is None:
        return None
    snap = {"id": uuid.uuid4().hex[:8], "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "issued_on": today(state).isoformat(), "reason": reason, "status": f["status"],
            "period_start": f["period_start"], "period_end": f["period_end"], "estimated_units": f["estimated_units"],
            "range": f["range"], "cost_rs": f["cost"]["rs"], "lines": f["lines"], "source_ids": f["source_ids"],
            "tariff_version": TARIFF_VERSION}
    state.setdefault("forecasts", []).append(snap)
    state["forecasts"] = state["forecasts"][-50:]
    return snap


# ---------- current cycle (needs meter readings) ----------
def current_cycle(state):
    bl = bills(state)
    anchors = []
    last_end = bl[-1]["end"] if bl else ""
    if bl and bl[-1].get("end_reading") is not None:
        anchors.append((d(bl[-1]["end"]), float(bl[-1]["end_reading"])))
    anchors += sorted((d(r["date"]), float(r["index_m3"])) for r in state.get("readings", []) if r["date"] > last_end)
    if len(anchors) < 2:
        return {"kind": "water", "status": "needs_readings",
                "status_message": "A current-month estimate needs two dated meter readings (or one reading plus the "
                                  "readings printed on your last bill). Bills alone cannot show this month's use."}
    (d0, i0), (d1, i1) = anchors[0], anchors[-1]
    days_measured = (d1 - d0).days
    rate = (i1 - i0) / days_measured if days_measured else 0.0
    start, n = next_cycle(state) if bl else (d0, DEFAULT_CYCLE)
    now = today(state)
    while start + timedelta(n) <= now:
        start += timedelta(n)
    end = start + timedelta(n)
    if d0 <= start:
        used = rate * (now - start).days                       # measured rate applied from the cycle start
        how = "measured daily rate x days so far"
    else:
        used = (i1 - i0) + rate * (now - d1).days
        how = "metered m3 since the reading + measured rate since then"
    left = (end - now).days
    est = used + rate * left
    sewer = state.get("profile", {}).get("sewer", False)
    return {"kind": "water", "status": "measured_projection", "period_start": start.isoformat(), "period_end": end.isoformat(),
            "metered_m3": round(i1 - i0, 2), "metered_days": days_measured, "measured_rate_l_per_day": round(rate * 1000),
            "used_so_far_m3": round(used, 2), "used_so_far_how": how, "days_left": left,
            "estimated_units": round(est, 2), "units": "m3", "cost": {"rs": tariff.water_bill(est, sewer).total,
                                                                      "how": "CWA tariff on the projected m3"},
            "source_readings": [a[0].isoformat() for a in anchors],
            "method": "measured_meter_rate", "assumptions": ["the measured daily rate continues for the rest of the cycle"]}
