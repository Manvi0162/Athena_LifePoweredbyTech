"""What-if scenarios and grounded recommendations (the explainable coach's evidence).

Every recommendation returns: period, projected cost, the data used, the method and limits,
a household-specific action, the quantified change (from the stated assumptions) and its status.
"""
import csv
import os

from . import actions
from .forecast import forecast

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
with open(os.path.join(DATA, "mu_household_benchmarks_2025.csv")) as _fh:
    BENCH = {r["indicator"]: float(r["value"]) for r in csv.DictReader(_fh)}


def scenario(household, key, params=None):
    """Baseline vs action for the current cycle: units, rupees and difference."""
    if key not in actions.CATALOGUE:
        raise KeyError(f"Unknown action '{key}'. Choose one of: {', '.join(actions.CATALOGUE)}")
    spec = actions.CATALOGUE[key]
    util = spec["utility"]
    p = actions.resolved_params(key, params, household)
    per_day = actions.saving_per_day(key, p, household)
    base = forecast(household, util)
    if base["status"] != "ok":
        return {"action": key, "status": base["status"], "message": base["message"]}
    new = forecast(household, util, extra_saving_per_day=per_day)
    return {
        "action": key, "title": spec["title"], "utility": util, "params": p, "status": "ok",
        "saving_units_per_day": round(per_day, 4), "unit": base["unit"],
        "period_start": base["period_start"], "period_end": base["period_end"], "days_left": base["days_left"],
        "baseline": {"units": base["units"]["mid"], "cost_rs": base["cost_rs"]["mid"]},
        "with_action": {"units": new["units"]["mid"], "cost_rs": new["cost_rs"]["mid"]},
        "difference": {"units": round(new["units"]["mid"] - base["units"]["mid"], 2),
                       "cost_rs": round(new["cost_rs"]["mid"] - base["cost_rs"]["mid"], 2)},
        "per_full_month": {"units": round(per_day * 30, 2), "cost_rs": _monthly_rs(household, util, base, per_day)},
        "formula": spec["formula"], "assumptions": spec["assumptions"],
        "limits": "Savings apply to the days left in this cycle; the full tariff is recalculated, not an average price.",
    }


def _monthly_rs(household, util, base, per_day):
    from .forecast import _bill
    m = base["daily_average"] * 30
    return round(_bill(util, max(m - per_day * 30, 0), 30, household).total - _bill(util, m, 30, household).total, 2)


def insights(household):
    people = max(1, int(household.get("members", 1)))
    out = {"utilities": {}, "recommendations": [], "benchmarks": []}
    total = 0.0
    for util in ("water", "electricity"):
        f = forecast(household, util)
        out["utilities"][util] = f
        if f["status"] != "ok":
            continue
        total += f["cost_rs"]["mid"]
        if util == "water":
            lpd = f["daily_average"] * 1000 / people
            ref = BENCH["water_domestic_l_per_person_day"]
            out["benchmarks"].append({"utility": "water", "you": round(lpd), "mauritius": ref, "unit": "L per person per day",
                                      "difference_pct": round((lpd / ref - 1) * 100), "source": "Statistics Mauritius 2025"})
        else:
            kwh_m = f["daily_average"] * 30
            ref = BENCH["electricity_domestic_kwh_per_consumer_month"]
            out["benchmarks"].append({"utility": "electricity", "you": round(kwh_m), "mauritius": ref, "unit": "kWh per month",
                                      "difference_pct": round((kwh_m / ref - 1) * 100), "source": "Statistics Mauritius 2025"})
        b = f.get("block") or {}
        if b.get("units_to_next_block") is not None and b["units_to_next_block"] < 0.15 * f["units"]["mid"] + 1:
            out["recommendations"].append({
                "kind": "block_warning", "utility": util,
                "title": f"Close to the next price block: {b['units_to_next_block']} {f['unit']} left",
                "detail": f"Above it, each {f['unit']} costs Rs {b['next_price']:.2f} instead of Rs {b['price_now']:.2f}.",
                "evidence": {"period_start": f["period_start"], "period_end": f["period_end"],
                             "projected_units": f["units"]["mid"], "method": "official tariff blocks"}})
    done = {a["key"] for a in household.get("actions", []) if a["status"] == "completed"}
    ranked = []
    for key in actions.CATALOGUE:
        s = scenario(household, key)
        if s["status"] == "ok" and s["per_full_month"]["cost_rs"] < 0:
            ranked.append(s)
    ranked.sort(key=lambda s: s["per_full_month"]["cost_rs"])
    for s in ranked[:4]:
        out["recommendations"].append({
            "kind": "action", "utility": s["utility"], "action": s["action"], "title": s["title"],
            "detail": f"Saves about {abs(s['per_full_month']['units'])} {s['unit']} and Rs {abs(s['per_full_month']['cost_rs']):.0f} a month.",
            "completed": s["action"] in done,
            "evidence": {k: s[k] for k in ("period_start", "period_end", "baseline", "with_action", "difference",
                                           "per_full_month", "formula", "assumptions", "params")}})
    out["total_projected_rs"] = round(total, 2)
    out["period_note"] = "Each utility uses its own current billing cycle."
    return out
