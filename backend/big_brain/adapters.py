"""Connect the real module outputs to Big Brain (report section 9, steps 1-2) and rank everything together
(report section 8, "unified ranking of all module recommendations": the next development step).

Each adapter turns a module's own /summary into the section-3 format. The numbers (savings, kWh, m3)
are the module's own calculations; nothing is recalculated here except the one cross-module action,
whose formula and assumptions are listed in full.
"""
from . import core

UTILITY_CONFIDENCE = {"better_supported": "medium", "preliminary": "low", "insufficient_data": "low"}


def _assumption_dict(items, period, extra=None):
    out = {"period": period, "currency": "MUR"}
    for i, a in enumerate(items or []):
        out[f"a{i + 1}"] = a["text"] if isinstance(a, dict) else str(a)
    out.update(extra or {})
    return out


def water_recommendations(summary):
    status = summary.get("status")
    rel = summary.get("reliability") or {}
    conf = UTILITY_CONFIDENCE.get(status, "low")
    if status == "better_supported" and rel.get("mean_abs_error_pct") is not None and rel["mean_abs_error_pct"] <= 10:
        conf = "high"
    period = f"{summary.get('period_start')} to {summary.get('period_end')}" if summary.get("period_start") else "next cycle"
    out = []
    for r in summary.get("recommendations") or []:
        ev = r.get("evidence") or {}
        out.append({"module": "water", "action_id": r["id"], "title": r["title"],
                    "estimated_savings_mur": round(max(r["saving"]["cost_rs"], 0), 2) if r.get("saving") else None,
                    "confidence": conf,
                    "evidence": {"calculation": ev.get("calculation"), "formula": ev.get("formula"),
                                 "litres_saved": (r.get("saving") or {}).get("litres"),
                                 "baseline": ev.get("baseline"), "with_action": ev.get("with_scenario"),
                                 "forecast_status": status, "cost_method": ev.get("cost_how")},
                    "assumptions": _assumption_dict(ev.get("assumptions"), period, {"note": ev.get("note")}),
                    "kind": "action", "status": r.get("status"), "detail": r.get("detail")})
    for a in summary.get("alerts") or []:
        out.append({"module": "water", "action_id": a["id"], "title": a["title"], "estimated_savings_mur": None,
                    "confidence": "medium", "evidence": a.get("evidence") or {},
                    "assumptions": {"period": period, "currency": "MUR"}, "kind": "alert", "detail": a.get("detail")})
    for u in summary.get("unlock") or []:
        out.append({"module": "water", "action_id": f"unlock_{u['scenario']}",
                    "title": f"Answer a question to unlock: {u['title']}", "estimated_savings_mur": None,
                    "confidence": "high", "evidence": {"missing": [m["prompt"] for m in u["missing"]]},
                    "assumptions": {"period": "not applicable", "currency": "MUR"}, "kind": "unlock"})
    return out


def electricity_recommendations(summary):
    fstatus = summary.get("forecast_status") or (summary.get("forecast") or {}).get("forecast_status")
    conf = (summary.get("forecast") or {}).get("confidence")
    conf = conf if conf in core.CONFIDENCE else UTILITY_CONFIDENCE.get(fstatus, "low")
    period = f"{summary.get('period_start')} to {summary.get('period_end')}" if summary.get("period_start") else "next cycle"
    out = []
    for r in summary.get("recommendations") or []:
        ev = r.get("evidence") or {}
        saving = r.get("saving") or {}
        kind = r.get("kind", "action")
        out.append({"module": "electricity", "action_id": r["id"], "title": r["title"],
                    "estimated_savings_mur": round(max(saving["cost_rs"], 0), 2) if saving.get("cost_rs") is not None else None,
                    "confidence": conf,
                    "evidence": {"kwh_saved": saving.get("kwh"), "formula": ev.get("formula"),
                                 "baseline": ev.get("baseline"), "with_action": ev.get("with_action"),
                                 "params": ev.get("params"), "forecast_status": fstatus},
                    "assumptions": _assumption_dict(ev.get("assumptions"), saving.get("per") or period,
                                                    {"limits": ev.get("limits")}),
                    "kind": "action" if kind == "action" else "alert", "status": r.get("status"),
                    "detail": r.get("detail")})
    budget = summary.get("budget") or {}
    if budget.get("status") in ("over", "at_risk"):
        out.append({"module": "electricity", "action_id": "budget", "estimated_savings_mur": None,
                    "title": "Over your electricity budget" if budget["status"] == "over" else
                             "Could go over your electricity budget", "confidence": conf, "evidence": budget,
                    "assumptions": {"period": period, "currency": "MUR"}, "kind": "alert"})
    return out


# ---------- one cross-module action (water x electricity) ----------
HOT_SHARE = 0.5          # assumed share of shower water that is heated
DELTA_T = 25.0           # degC: about 25 degC mains water heated to about 50 degC
HEATER_EFFICIENCY = 0.9  # electric resistance heater
KJ_PER_L_DEGC = 4.186


def cross_module_recommendations(water_state, water_summary, elec_state, elec_forecast):
    """Shorter showers save water AND electricity when water is heated electrically (E3 = electric).
    Litres from the water engine; kWh from physics with the assumptions shown; rupees from each tariff."""
    from electricity import tariff as etariff
    assessment = (elec_state or {}).get("assessment") or {}
    heating = str(assessment.get("water_heating") or assessment.get("E3") or "").strip().lower()
    shower = next((r for r in (water_summary or {}).get("recommendations") or [] if r["id"] == "shorter_showers"), None)
    if heating != "electric" or not shower or (elec_forecast or {}).get("status") != "ok":
        return []
    litres = shower["saving"]["litres"]
    kwh = litres * HOT_SHARE * KJ_PER_L_DEGC * DELTA_T / 3600 / HEATER_EFFICIENCY
    profile = elec_state.get("profile", {})
    base_kwh = elec_forecast["kwh"]["mid"]
    tariff_code, tv = profile.get("ceb_tariff", "140"), profile.get("tv_licence", True)
    elec_rs = round(etariff.electricity_bill(base_kwh, tariff_code, tv).total -
                    etariff.electricity_bill(max(base_kwh - kwh, 0), tariff_code, tv).total, 2)
    water_rs = shower["saving"]["cost_rs"]
    return [{"module": "water", "action_id": "shorter_showers_hot_water",
             "title": "Shorter showers: less water and less water-heater electricity",
             "estimated_savings_mur": round(water_rs + elec_rs, 2), "confidence": "low",
             "evidence": {"litres_saved": litres, "water_saving_mur": water_rs, "kwh_saved": round(kwh, 1),
                          "electricity_saving_mur": elec_rs,
                          "calculation": f"{litres:,} L x {HOT_SHARE:g} hot x {KJ_PER_L_DEGC} kJ/L/degC x {DELTA_T:g} degC "
                                         f"/ 3600 / {HEATER_EFFICIENCY:g} = {kwh:.1f} kWh",
                          "sources": "water: water engine scenario; electricity: CEB tariff on the electricity forecast"},
             "assumptions": {"period": "next billing cycle", "currency": "MUR", "hot_share": HOT_SHARE,
                             "delta_t_c": DELTA_T, "heater_efficiency": HEATER_EFFICIENCY,
                             "condition": "Electricity question 3 = electric water heating"},
             "kind": "cross_module"}]


# ---------- unified ranking (Manvi's score, applied to every recommendation) ----------
def score(rec, main_goal=None):
    """priority = 0.40 impact + 0.35 urgency + 0.25 confidence (same weights as rank_actions)."""
    s = rec.get("estimated_savings_mur")
    kind = rec.get("kind", "action")
    if kind == "alert":
        impact = 3 if rec["action_id"] in ("check_for_leaks", "budget") else 2
        urgency = 3
    elif kind == "unlock":
        impact, urgency = 1, 1
    else:
        impact = 3 if (s or 0) >= 200 else 2 if (s or 0) >= 50 else 1
        urgency = 2
    if rec.get("status") == "completed":
        urgency = 0
    conf = {"high": 3, "medium": 2, "low": 1}[rec["confidence"]]
    total = 0.40 * impact + 0.35 * urgency + 0.25 * conf
    reasons = [f"impact {impact}", f"urgency {urgency}", f"confidence {conf}"]
    if main_goal in ("reduce_food_waste",) and rec["module"] == "food":
        total += 0.3
        reasons.append("+0.3 your goal: reduce food waste")
    elif main_goal in ("conserve_resources",) and rec["module"] in ("water", "electricity") and kind != "unlock":
        total += 0.2
        reasons.append("+0.2 your goal: conserve water and electricity")
    elif main_goal in ("reduce_expenses", "all") and s:
        total += 0.2
        reasons.append("+0.2 your goal: reduce monthly expenses")
    return round(total, 2), ", ".join(reasons)


def rank_all(combined, main_goal=None):
    out = []
    for a in combined:
        if a["source"] == "domain_module":
            a["priority_score"], a["priority_reason"] = score(a, main_goal)
        else:
            a["priority_reason"] = "Big Brain data-quality check (impact, urgency, confidence)"
        out.append(a)
    out.sort(key=lambda a: (-a["priority_score"], -(a.get("estimated_savings_mur") or 0), a["module"], a["action_id"]))
    for i, a in enumerate(out, 1):
        a["rank"] = i
    return out
