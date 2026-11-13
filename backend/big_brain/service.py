"""Big Brain pipeline for one household (report section 2):
1 collect inputs -> 2 validate data -> 3 combine recommendations -> 4 rank actions -> 5 explanations -> JSON.

Inputs come from every module at once:
  water       : water engine state + /water/summary (forecast, recommendations with savings, alerts, unlocks)
  electricity : electricity engine state + /electricity/summary and forecast
  food        : receipts, receipt items, pantry and recipes (shared tables) + the food module's recommendations
  household   : the onboarding answers (members, goal, monthly target) shared by all modules
"""
from datetime import date

from . import adapters, core, explain

MONTH_NOTE = ("Utilities are next-cycle estimates; groceries are confirmed purchases this month. They cover "
              "different periods, so no single household total is claimed.")


def _food_inputs(db, household_id):
    recipes = (db.table("lb_recipes").select("id,name,verification_status,lb_recipe_ingredients"
                                             "(ingredient_name,quantity,unit,optional)").execute().data or [])
    return recipes


def _water():
    from water import advice as wadvice
    from water import store as wstore
    s = wstore.load()
    return s, wadvice.summary(s)


def _electricity():
    from electricity import advice as eadvice
    from electricity import forecast as eforecast
    from electricity import store as estore
    s = estore.load()
    return s, eadvice.summary(s), eforecast.forecast(s)


def outlook(household, water_summary, elec_forecast, receipts, today=None):
    today = today or date.today()
    month = today.strftime("%Y-%m")
    w = water_summary
    if w.get("forecast"):
        water = {"label": "forecast", "status": w["status"], "status_message": w["status_message"],
                 "period_start": w["period_start"], "period_end": w["period_end"], "amount": w["forecast"]["amount"],
                 "unit": "m3", "cost_rs": w["forecast"]["cost_rs"], "cost_low_rs": w["forecast"]["cost_low_rs"],
                 "cost_high_rs": w["forecast"]["cost_high_rs"]}
    else:
        water = {"label": "insufficient_data", "status": w.get("status"), "status_message": w.get("status_message")}
    e = elec_forecast
    if e.get("status") == "ok":
        elec = {"label": "forecast", "status": e.get("forecast_status"), "period_start": e["period_start"],
                "period_end": e["period_end"], "amount": e["kwh"]["mid"], "unit": "kWh", "cost_rs": e["cost_rs"]["mid"],
                "cost_low_rs": e["cost_rs"]["low"], "cost_high_rs": e["cost_rs"]["high"]}
    else:
        elec = {"label": "insufficient_data", "status": e.get("forecast_status") or e.get("status"),
                "status_message": e.get("message")}
    month_receipts = [r for r in receipts if str(r.get("receipt_date") or r.get("created_at") or "")[:7] == month]
    groceries = {"label": "actual", "month": month, "recorded_rs": round(sum(float(r["total"] or 0) for r in month_receipts), 2),
                 "receipts": len(month_receipts), "all_time_rs": round(sum(float(r["total"] or 0) for r in receipts), 2)}
    utilities_total = (round(water["cost_rs"] + elec["cost_rs"], 2)
                       if water["label"] == "forecast" and elec["label"] == "forecast" else None)
    target = (household.get("budget_goals") or {}).get("monthly_target")
    return {"water": water, "electricity": elec, "groceries": groceries,
            "utilities_estimate_rs": utilities_total,
            "utilities_note": None if utilities_total is None else
            f"Water {water['period_start']} to {water['period_end']} + electricity {elec['period_start']} to "
            f"{elec['period_end']} (each module's own next billing cycle).",
            "household_total_rs": None, "household_total_note": MONTH_NOTE,
            "monthly_target_rs": target,
            "target_check": None if not target or utilities_total is None else {
                "utilities_estimate_plus_groceries_so_far_rs": round(utilities_total + groceries["recorded_rs"], 2),
                "share_of_target_pct": round((utilities_total + groceries["recorded_rs"]) / target * 100),
                "note": "Mixes next-cycle estimates and this month's actual groceries; a guide, not a bill."}}


def build_dashboard(ctx, household, use_ai=True):
    wstate, wsum = _water()
    estate, esum, eforecast = _electricity()
    data = core.collect_household_data(ctx.db, household["id"],
                                       module_bills={"water": wstate.get("bills", []), "electricity": estate.get("bills", [])})
    verification = core.verify_household_data(data)
    context = core.build_decision_context(data, verification)
    big_brain_actions = core.rank_actions(core.generate_action_candidates(context))
    from recipes.recommendations import food_recommendations
    food = food_recommendations(data["food"]["pantry"], data["food"]["receipt_items"], _food_inputs(ctx.db, household["id"]))
    water_recs = adapters.water_recommendations(wsum) + adapters.cross_module_recommendations(wstate, wsum, estate, eforecast)
    elec_recs = adapters.electricity_recommendations(esum)
    domain = core.collect_domain_recommendations(food_results=food, water_results=water_recs, electricity_results=elec_recs)
    combined = core.combine_big_brain_actions(big_brain_actions, domain)
    goal = (household.get("preferences") or {}).get("main_goal")
    ranked = adapters.rank_all(combined, goal)
    explain.explain_ranked_actions(context, ranked, use_ai=use_ai)
    module_status = {
        "food": "data_available" if data["food"]["receipts"] or data["food"]["pantry"] else "insufficient_data",
        "water": "insufficient_data" if wsum.get("status") == "insufficient_data" else "data_available",
        "electricity": "data_available" if eforecast.get("status") == "ok" else "insufficient_data"}
    dash = core.build_integrated_dashboard(household["id"], context, ranked, module_status)
    dash["outlook"] = outlook(household, wsum, eforecast, data["food"]["receipts"])
    dash["verification"] = {"receipt_issues": verification["issues"],
                            "possible_duplicates": verification["possible_duplicates"]}
    dash["module_details"] = {
        "water": {k: wsum.get(k) for k in ("status", "status_message", "data_completeness", "reliability",
                                            "forecast_vs_actual", "context")},
        "electricity": {k: esum.get(k) for k in ("forecast_status", "data_completeness", "benchmark", "budget")}}
    dash["method"] = ("Each module calculates its own forecast and savings; the AI recommendation engine validates the inputs, ranks every "
                      "action with 0.40 impact + 0.35 urgency + 0.25 confidence (+ your main goal), and Gemini only "
                      "phrases the explanations (numbers checked).")
    return dash


def insights_for_ui(dash):
    """The app's Insight shape (livebetter/src/types.ts) + the full Big Brain dashboard fields."""
    o = dash["outlook"]
    w, e = o["water"], o["electricity"]
    period = w if w["label"] == "forecast" else e
    top = [a for a in dash["actions"] if a.get("kind") != "unlock"][:5]
    return {**dash,
            "period_start": period.get("period_start"), "period_end": period.get("period_end"), "currency": "MUR",
            "water": w.get("cost_rs"), "electricity": e.get("cost_rs"), "groceries_recorded": o["groceries"]["recorded_rs"],
            "total": None,
            "assumptions": [o["household_total_note"]] + ([o["utilities_note"]] if o["utilities_note"] else []) +
                           ["Forecast costs are calculated with the official CWA and CEB tariffs.",
                            "Grocery spending counts confirmed receipts only; cooking never adds a second expense."],
            "recommendations": [a["explanation"] for a in top],
            "source_data": [a["action_id"] for a in dash["actions"]]}
