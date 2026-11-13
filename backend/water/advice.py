"""What-if scenarios, grounded recommendations and the module summary read by the Household AI.

Every recommendation carries its evidence: period, data used, method, assumptions, the household-specific action,
the quantified change and whether it was completed.
"""
import csv
import os

from . import actions
from .forecast import bill_for, forecast
from .history import measured_periods, today

DATA = os.path.join(os.path.dirname(__file__), "data")
MU_L_PER_PERSON_DAY = 198.9      # Statistics Mauritius ESI 1929 (2025), Table 1: domestic tariff
MU_M3_PER_SUBSCRIBER_YEAR = 225  # same report, Table 16
UNUSUAL_RATIO = 1.3              # latest rate 30% above the usual rate -> "check for leaks"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REGIONS = ["North", "South", "East", "West", "Centre"]


def _csv(name):
    with open(os.path.join(DATA, name)) as fh:
        return list(csv.DictReader(fh))


RESERVOIRS = _csv("mu_reservoir_levels_monthly_2024_2025.csv")
RAINFALL = _csv("mu_rainfall_monthly_by_region_2024_2025.csv")


def scenario(state, key, params=None):
    """Baseline vs action for the current cycle, plus the effect over a full month."""
    p = actions.resolved_params(key, params, state.get("profile", {}))
    per_day = actions.saving_per_day(key, p, state.get("profile", {}))
    base = forecast(state)
    if base["status"] != "ok":
        return {"action": key, "status": base["status"], "message": base["message"]}
    new = forecast(state, extra_saving_per_day=per_day)
    month = base["daily_average_m3"] * 30
    month_rs = round(bill_for(state, max(month - per_day * 30, 0)).total - bill_for(state, month).total, 2)
    spec = actions.CATALOGUE[key]
    return {
        "action": key, "title": spec["title"], "status": "ok", "params": p,
        "saving_litres_per_day": round(per_day * 1000, 1), "saving_m3_per_day": round(per_day, 4),
        "period_start": base["period_start"], "period_end": base["period_end"], "days_left": base["days_left"],
        "baseline": {"m3": base["m3"]["mid"], "cost_rs": base["cost_rs"]["mid"]},
        "with_action": {"m3": new["m3"]["mid"], "cost_rs": new["cost_rs"]["mid"]},
        "difference": {"m3": round(new["m3"]["mid"] - base["m3"]["mid"], 2),
                       "cost_rs": round(new["cost_rs"]["mid"] - base["cost_rs"]["mid"], 2)},
        "per_full_month": {"m3": round(-per_day * 30, 2), "litres": round(-per_day * 30000), "cost_rs": month_rs},
        "formula": spec["formula"], "assumptions": spec["assumptions"],
        "limits": "Applies to the days left in this cycle. The whole CWA tariff is recalculated, not an average price. "
                  "Below Rs 45 of water charges the minimum charge applies, so small savings may show Rs 0.",
    }


def unusual_usage(state):
    """Latest measured period vs the household's usual rate (possible leak)."""
    periods = measured_periods(state)
    if len(periods) < 3:
        return None
    rate = lambda p: p["m3"] / max((p["end"] - p["start"]).days, 1)
    latest, usual = rate(periods[-1]), sum(rate(p) for p in periods[:-1]) / (len(periods) - 1)
    if usual <= 0 or latest < UNUSUAL_RATIO * usual:
        return None
    return {"latest_m3_per_day": round(latest, 3), "usual_m3_per_day": round(usual, 3),
            "increase_pct": round((latest / usual - 1) * 100),
            "period_start": periods[-1]["start"].isoformat(), "period_end": periods[-1]["end"].isoformat()}


def context(state):
    """Season context from Statistics Mauritius: reservoirs and rainfall for this month (2024-2025 data)."""
    month = MONTHS[today(state).month - 1]
    region = state.get("profile", {}).get("region") or "Island of Mauritius"
    res = {r["year"]: r for r in RESERVOIRS if r["reservoir"] == "All reservoirs" and r["month"] == month}
    rain_rows = [r for r in RAINFALL if r["region"] == region]
    this = next(r for r in rain_rows if r["month"] == month)
    yearly_avg = sum(float(r["long_term_mean_1991_2020_mm"]) for r in rain_rows) / 12
    mean = float(this["long_term_mean_1991_2020_mm"])
    dry = mean < 0.75 * yearly_avg
    return {
        "month": month, "region": region,
        "reservoirs_all_pct": {"normal_1990_1999": float(res["2024"]["normal_1990_1999_pct"]),
                               "2024": float(res["2024"]["mean_pct"]), "2025": float(res["2025"]["mean_pct"])},
        "rain_long_term_mean_mm": mean, "rain_monthly_average_mm": round(yearly_avg, 1), "dry_month": dry,
        "message": (f"{month} is usually a dry month in {region} ({mean:.0f} mm of rain vs {yearly_avg:.0f} mm in an average month). "
                    if dry else f"{month} usually brings {mean:.0f} mm of rain in {region}. ")
                   + f"All reservoirs averaged {float(res['2025']['mean_pct']):.0f}% in {month} 2025 "
                     f"(normal {float(res['2024']['normal_1990_1999_pct']):.0f}%).",
        "source": "Statistics Mauritius, Energy and Water Statistics 2025, Tables 13-14 (past years, not live levels)",
    }


def _budget(state, f):
    budget = state.get("profile", {}).get("monthly_budget_rs")
    if not budget or f["status"] != "ok":
        return None
    status = "over" if f["cost_rs"]["mid"] > budget else "at_risk" if f["cost_rs"]["high"] > budget else "ok"
    return {"budget_rs": budget, "projected_rs": f["cost_rs"]["mid"], "high_rs": f["cost_rs"]["high"], "status": status}


def insights(state):
    f = forecast(state)
    out = {"module": "water", "forecast": f, "recommendations": [], "benchmark": None, "budget": None,
           "context": context(state)}
    if f["status"] != "ok":
        return out
    people = max(1, int(state.get("profile", {}).get("members", 1)))
    lpd = f["daily_average_m3"] * 1000 / people
    out["benchmark"] = {"you_l_per_person_day": round(lpd), "mauritius_l_per_person_day": MU_L_PER_PERSON_DAY,
                        "difference_pct": round((lpd / MU_L_PER_PERSON_DAY - 1) * 100),
                        "source": "Statistics Mauritius 2025, domestic tariff average"}
    out["budget"] = _budget(state, f)
    ev = {"period_start": f["period_start"], "period_end": f["period_end"], "projected_m3": f["m3"]["mid"],
          "method": f["method"], "source_data": f["source_data"]}
    leak = unusual_usage(state)
    if leak:
        out["recommendations"].append({
            "id": "check_for_leaks", "kind": "alert",
            "title": f"Water use is {leak['increase_pct']}% above your usual",
            "detail": "Check for leaks: close every tap, note the meter, wait 30 minutes without using water. "
                      "If the meter moved, there is a leak (often a toilet or a garden pipe).",
            "evidence": {**ev, **leak, "method": f"latest measured period vs average of earlier ones (alert at +{round((UNUSUAL_RATIO - 1) * 100)}%)"}})
    b = f["block"] or {}
    if b.get("m3_to_next_block") is not None and b["m3_to_next_block"] < 0.15 * f["m3"]["mid"] + 1:
        out["recommendations"].append({
            "id": "next_price_block", "kind": "alert",
            "title": f"{b['m3_to_next_block']} m3 before the next price block",
            "detail": f"Above it each m3 costs Rs {b['next_price']:.2f} instead of Rs {b['price_now']:.2f}.",
            "evidence": {**ev, "method": "CWA rising-block tariff"}})
    if out["budget"] and out["budget"]["status"] != "ok":
        bb = out["budget"]
        out["recommendations"].append({
            "id": "budget", "kind": "alert",
            "title": "Over your water budget" if bb["status"] == "over" else "Could go over your water budget",
            "detail": f"Projected Rs {bb['projected_rs']:.0f} (up to Rs {bb['high_rs']:.0f}) vs your budget of Rs {bb['budget_rs']:.0f}.",
            "evidence": {**ev, **bb}})
    done = {a["key"]: a for a in state.get("actions", [])}
    ranked = [s for s in (scenario(state, k) for k in actions.CATALOGUE) if s["status"] == "ok"]
    ranked.sort(key=lambda s: (s["per_full_month"]["cost_rs"], s["per_full_month"]["m3"]))
    for s in ranked:
        a = done.get(s["action"])
        out["recommendations"].append({
            "id": s["action"], "kind": "action", "title": s["title"],
            "detail": f"Saves about {abs(s['per_full_month']['litres']):,} L and Rs {abs(s['per_full_month']['cost_rs']):.0f} a month.",
            "status": a["status"] if a else "suggested",
            "saving": {"m3": abs(s["per_full_month"]["m3"]), "litres": abs(s["per_full_month"]["litres"]),
                       "cost_rs": abs(s["per_full_month"]["cost_rs"]), "per": "month"},
            "evidence": {k: s[k] for k in ("period_start", "period_end", "baseline", "with_action", "difference",
                                           "per_full_month", "formula", "assumptions", "params", "limits")}})
    return out


def summary(state):
    """The shared module contract (see backend/MODULE_CONTRACT.md): what the Household AI reads."""
    i = insights(state)
    f = i["forecast"]
    out = {"module": "water", "status": f["status"], "currency": "MUR",
           "recent_activity": list(reversed(state.get("activity", [])))[:10]}
    if f["status"] != "ok":
        return {**out, "message": f["message"]}
    return {**out,
            "period_start": f["period_start"], "period_end": f["period_end"],
            "forecast": {"amount": f["m3"]["mid"], "unit": "m3", "low": f["m3"]["low"], "high": f["m3"]["high"],
                         "cost_rs": f["cost_rs"]["mid"], "cost_low_rs": f["cost_rs"]["low"],
                         "cost_high_rs": f["cost_rs"]["high"], "confidence": f["confidence"], "method": f["method"]},
            "benchmark": i["benchmark"], "budget": i["budget"], "context": i["context"]["message"],
            "recommendations": [{"id": r["id"], "kind": r["kind"], "title": r["title"], "detail": r["detail"],
                                 "saving": r.get("saving"), "status": r.get("status"), "evidence": r["evidence"]}
                                for r in i["recommendations"]]}
