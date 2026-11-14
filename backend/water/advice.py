"""Insights, year outlook, context and the module summary read by the lead AI.

Every recommendation carries its evidence. Scenarios that lack data are listed as "unlock" items with the exact
question to answer, instead of a guessed saving.
"""
import csv
import os
from datetime import date, timedelta

from . import assessment as A
from . import scenarios as SC
from . import seasonality as S
from . import tariff
from .forecast import (all_checks, bills, completeness, core, current_cycle, days_of, forecast, reliability,
                       shape, today, usual_day)

DATA = os.path.join(os.path.dirname(__file__), "data")
MU_L_PER_PERSON_DAY = 198.9      # Statistics Mauritius ESI 1929 (2025), Table 1: domestic tariff
UNUSUAL_RATIO = 1.3              # latest bill 30% or more above the earlier ones -> "check for leaks"
TARIFF_CHECK_RS = 5.0
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _csv(name):
    with open(os.path.join(DATA, name)) as fh:
        return list(csv.DictReader(fh))


RESERVOIRS = _csv("mu_reservoir_levels_monthly_2024_2025.csv")
RAINFALL = _csv("mu_rainfall_monthly_by_region_2024_2025.csv")
PRODUCTION = _csv("mu_potable_production_monthly_2024_2025.csv")


def tariff_check(state, bill):
    """Compare the amount the user confirmed with our CWA tariff calculation for the same m3."""
    if bill.get("amount_rs") is None:
        return None
    ours = tariff.water_bill(float(bill["m3"]), state.get("profile", {}).get("sewer", False)).total
    diff = round(float(bill["amount_rs"]) - ours, 2)
    return {"bill_amount_rs": bill["amount_rs"], "tariff_calculated_rs": ours, "difference_rs": diff,
            "ok": abs(diff) <= TARIFF_CHECK_RS,
            "message": None if abs(diff) <= TARIFF_CHECK_RS else
            f"Your bill says Rs {bill['amount_rs']:.2f} but the CWA tariff gives Rs {ours:.2f} for {bill['m3']:g} m3. "
            "Check the m3, the sewer setting, or arrears/other fees on the bill."}


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
    supply = {}
    for y in ("2024", "2025"):
        rows = [r for r in PRODUCTION if r["year"] == y]
        avg = sum(float(r["production_mm3"]) for r in rows) / sum(int(r["days"]) for r in rows)
        this_m = next(r for r in rows if int(r["month"]) == MONTHS.index(month) + 1)
        supply[y] = round((float(this_m["mm3_per_day"]) / avg - 1) * 100, 1)
    return {
        "month": month, "region": region,
        "reservoirs_all_pct": {"normal_1990_1999": float(res["2024"]["normal_1990_1999_pct"]),
                               "2024": float(res["2024"]["mean_pct"]), "2025": float(res["2025"]["mean_pct"])},
        "rain_long_term_mean_mm": mean, "rain_monthly_average_mm": round(yearly_avg, 1), "dry_month": dry,
        "cwa_production_vs_year_pct": supply,
        "message": (f"{month} is usually a dry month in {region} ({mean:.0f} mm of rain vs {yearly_avg:.0f} mm in an average month). "
                    if dry else f"{month} usually brings {mean:.0f} mm of rain in {region}. ")
                   + f"All reservoirs averaged {float(res['2025']['mean_pct']):.0f}% in {month} 2025 "
                     f"(normal {float(res['2024']['normal_1990_1999_pct']):.0f}%).",
        "supply_note": "CWA production per day this month vs the yearly average (Table 15). It shows supply, which is "
                       "limited by reservoirs and cuts, so it is context, not household demand.",
        "source": "Statistics Mauritius, Energy and Water Statistics 2025, Tables 13-15 (past years, not live levels)",
    }


def year_outlook(state):
    """Expected m3 and bill for a 30-day bill starting in each month, from this household's measured use."""
    bl = bills(state)
    if not bl:
        return {"module": "water", "status": "insufficient_data",
                "status_message": "Add your first bill to see how your bill may change through the year."}
    profile = state.get("profile", {})
    usual = usual_day(bl[-3:], profile)
    year = today(state).year
    months = []
    for m in range(1, 13):
        first = date(year, m, 1)
        m3 = usual * sum(shape(first + timedelta(i), profile) for i in range(30))
        months.append({"month": MONTHS[m - 1], "m3": round(m3, 2), "cost_rs": tariff.water_bill(m3, profile.get("sewer", False)).total,
                       "factor": round(S.season_factor(first, profile), 3), "summer": m in S.SUMMER_MONTHS})
    lo, hi = min(months, key=lambda x: x["cost_rs"]), max(months, key=lambda x: x["cost_rs"])
    return {"module": "water", "status": "preliminary" if len(bl) < 3 else "ok", "usual_day_m3": round(usual, 4),
            "months": months, "cheapest": lo["month"], "dearest": hi["month"],
            "difference_rs": round(hi["cost_rs"] - lo["cost_rs"], 2),
            "method": "your measured use (season removed) x weekend x month temperature factor, 30 days; CWA tariff",
            "note": "Unchanged habits assumed. Habit changes are what-if scenarios.",
            "seasonality": S.explain(profile, list(range(1, 13)))}


def unusual_usage(state):
    bl = bills(state)
    if len(bl) < 3:
        return None
    rate = lambda b: float(b["m3"]) / max(days_of(b), 1)
    latest, usual = rate(bl[-1]), sum(rate(b) for b in bl[:-1]) / (len(bl) - 1)
    if usual <= 0 or latest < UNUSUAL_RATIO * usual:
        return None
    return {"latest_l_per_day": round(latest * 1000), "usual_l_per_day": round(usual * 1000),
            "increase_pct": round((latest / usual - 1) * 100), "bill_id": bl[-1]["id"]}


def insights(state):
    f = forecast(state)
    out = {"module": "water", "status": f["status"], "status_message": f["status_message"], "forecast": f,
           "alerts": [], "recommendations": [], "unlock": [], "benchmark": None, "budget": None,
           "context": context(state), "defaults": A.MAURITIUS_DEFAULTS}
    members = state.get("household", {}).get("members")
    if f["estimated_units"] is not None:
        if members:
            lpd = f["observed_vs_assumed"]["observed_m3_per_day"] * 1000 / members
            out["benchmark"] = {"you_l_per_person_day": round(lpd), "mauritius_l_per_person_day": MU_L_PER_PERSON_DAY,
                                "difference_pct": round((lpd / MU_L_PER_PERSON_DAY - 1) * 100),
                                "source": "Statistics Mauritius 2025, domestic tariff average", "basis": "your confirmed bills"}
        budget = state.get("profile", {}).get("monthly_budget_rs")
        if budget:
            st = "over" if f["cost"]["rs"] > budget else "at_risk" if f["cost"]["high_rs"] > budget else "ok"
            out["budget"] = {"budget_rs": budget, "projected_rs": f["cost"]["rs"], "high_rs": f["cost"]["high_rs"], "status": st}
            if st != "ok":
                out["alerts"].append({"id": "budget", "title": "Over your water budget" if st == "over" else "Could go over your water budget",
                                      "detail": f"Estimated Rs {f['cost']['rs']:.0f} (up to Rs {f['cost']['high_rs']:.0f}) vs your budget of Rs {budget:.0f}.",
                                      "evidence": {"forecast_period": [f["period_start"], f["period_end"]], **out["budget"]}})
        b = f["block"] or {}
        if b.get("m3_to_next_block") is not None and b["m3_to_next_block"] < 0.15 * f["estimated_units"] + 1:
            out["alerts"].append({"id": "next_price_block", "title": f"{b['m3_to_next_block']} m3 before the next price block",
                                  "detail": f"Above it each m3 costs Rs {b['next_price']:.2f} instead of Rs {b['price_now']:.2f}.",
                                  "evidence": {"estimated_m3": f["estimated_units"], "method": "CWA rising-block tariff"}})
        leak = unusual_usage(state)
        if leak:
            out["alerts"].append({"id": "check_for_leaks", "title": f"Your latest bill is {leak['increase_pct']}% above your usual",
                                  "detail": "Check for leaks: close every tap, note the meter, wait 30 minutes without using "
                                            "water. If the meter moved, there is a leak (often a toilet or a garden pipe).",
                                  "evidence": {**leak, "method": "latest bill vs average of earlier bills (alert at +30%)"}})
        tc = tariff_check(state, bills(state)[-1])
        if tc and not tc["ok"]:
            out["alerts"].append({"id": "tariff_mismatch", "title": "Bill amount differs from the tariff", "detail": tc["message"],
                                  "evidence": tc})
    goals = {a["key"]: a for a in state.get("actions", [])}
    ranked = []
    for key, spec in SC.CATALOGUE.items():
        if spec["direction"] != "less":
            continue
        r = SC.run(state, key, {})
        if r["status"] == "needs_input":
            out["unlock"].append({"scenario": key, "title": spec["title"], "missing": r["missing"]})
        elif r["status"] == "ok":
            ranked.append(r)
    ranked.sort(key=lambda r: (r["difference"]["rs"], r["difference"]["litres"]))
    for r in ranked:
        a = goals.get(r["scenario"])
        out["recommendations"].append({
            "id": r["scenario"], "kind": "action", "title": r["title"],
            "detail": f"About {abs(r['difference']['litres']):,} L and Rs {abs(r['difference']['rs']):.0f} less in the next bill period.",
            "status": a["status"] if a else "suggested",
            "saving": {"litres": abs(r["difference"]["litres"]), "m3": abs(r["difference"]["m3"]), "cost_rs": abs(r["difference"]["rs"]),
                       "per": f"{r['period_start']} to {r['period_end']}"},
            "evidence": {k: r[k] for k in ("calculation", "formula", "assumptions", "baseline", "with_scenario", "cost_how", "note")}})
    return out


def summary(state):
    """Shared module contract (backend/MODULE_CONTRACT.md) + the honesty fields of the 13 Nov spec."""
    i = insights(state)
    f = i["forecast"]
    out = {"module": "water", "status": f["status"], "status_message": f["status_message"], "currency": "MUR",
           "data_completeness": f["data_completeness"], "reliability": f["reliability"],
           "assessment_complete": f["assessment_complete"],
           "forecast_vs_actual": all_checks(state)[-6:],
           "current_cycle": current_cycle(state),
           "recent_activity": list(reversed(state.get("activity", [])))[:10],
           "context": i["context"]["message"], "unlock": i["unlock"]}
    if f["estimated_units"] is None:
        return {**out, "forecast": None, "recommendations": [], "alerts": []}
    return {**out, "period_start": f["period_start"], "period_end": f["period_end"],
            "forecast": {"amount": f["estimated_units"], "unit": "m3", "low": f["range"]["low"], "high": f["range"]["high"],
                         "cost_rs": f["cost"]["rs"], "cost_low_rs": f["cost"]["low_rs"], "cost_high_rs": f["cost"]["high_rs"],
                         "status": f["status"], "method": f["method_explained"], "lines": f["lines"],
                         "source_ids": f["source_ids"]},
            "benchmark": i["benchmark"], "budget": i["budget"], "alerts": i["alerts"],
            "recommendations": i["recommendations"]}
