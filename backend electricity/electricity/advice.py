
"""What-if scenarios, grounded recommendations and the module summary read by Household AI."""

from . import actions
from .forecast import bill_for, forecast
from .history import measured_periods

MU_KWH_PER_MONTH = 201.5
UNUSUAL_RATIO = 1.3

APPLIANCE_NAMES = {
    "air_conditioner": "Air conditioner",
    "water_heater": "Electric water heater",
    "washing_machine": "Washing machine"
}


def _action_params(key):
    return dict(actions.CATALOGUE[key]["params"])


def _selected_appliances(state):
    assessment = state.get("assessment", {}) or {}
    selected = assessment.get("appliances", assessment.get("E1", []))

    if isinstance(selected, str):
        selected = [selected]

    if not isinstance(selected, (list, tuple, set)):
        return set()

    return {str(item).strip().lower() for item in selected}


def _eligible_actions(state):
    """Build recommendations only for appliances selected by the household."""
    eligible = []

    for appliance in APPLIANCE_NAMES:
        if appliance not in _selected_appliances(state):
            continue

        params = _action_params("appliance_hours")
        params["appliance"] = appliance

        allowed, _ = actions.eligibility(
            "appliance_hours", params, state
        )

        if allowed:
            eligible.append(("appliance_hours", params))

    # Standby saving is available to every household.
    params = _action_params("standby_off")
    allowed, _ = actions.eligibility("standby_off", params, state)

    if allowed:
        eligible.append(("standby_off", params))

    # Cooking requires the user to provide the appliance's rated power.
    assessment = state.get("assessment", {}) or {}
    cooking_kw = assessment.get(
        "cooking_kw",
        assessment.get("cooking_appliance_kw")
    )

    if cooking_kw is not None:
        params = _action_params("cooking_hours")
        params["kw"] = cooking_kw

        allowed, _ = actions.eligibility(
            "cooking_hours", params, state
        )

        if allowed:
            eligible.append(("cooking_hours", params))

    return eligible


def scenario(state, key, params=None):
    raw_params = params or {}
    p = actions.resolved_params(
        key, raw_params, state.get("profile", {})
    )

    allowed, message = actions.eligibility(key, p, state)

    if not allowed:
        return {
            "action": key,
            "status": "needs_input",
            "message": message
        }

    per_day = actions.saving_per_day(
        key, p, state.get("profile", {})
    )

    base = forecast(state)

    if base.get("status") != "ok":
        return {
            "action": key,
            "status": base.get("status", "insufficient_data"),
            "message": base.get(
                "message",
                "Add a confirmed bill or sufficient meter readings first."
            )
        }

    new = forecast(state, extra_saving_per_day=per_day)
    spec = actions.CATALOGUE[key]

    if key == "appliance_hours":
        estimated_power = raw_params.get("kw") is None
    elif key == "standby_off":
        estimated_power = raw_params.get("standby_watts") is None
    else:
        estimated_power = False

    assumptions = list(spec["assumptions"])

    if estimated_power:
        assumptions.append(
            "Appliance power uses an estimated default rating."
        )

    title = spec["title"]

    if key == "appliance_hours":
        title = f"Use the {APPLIANCE_NAMES.get(p['appliance'], p['appliance'])} less"

    return {
        "action": key,
        "title": title,
        "status": "ok",
        "params": p,
        "power_estimated": estimated_power,
        "saving_kwh_per_day": round(per_day, 4),
        "period_start": base["period_start"],
        "period_end": base["period_end"],
        "days": base["days"],
        "baseline": {
            "kwh": base["kwh"]["mid"],
            "cost_rs": base["cost_rs"]["mid"]
        },
        "with_action": {
            "kwh": new["kwh"]["mid"],
            "cost_rs": new["cost_rs"]["mid"]
        },
        "difference": {
            "kwh": round(new["kwh"]["mid"] - base["kwh"]["mid"], 2),
            "cost_rs": round(new["cost_rs"]["mid"] - base["cost_rs"]["mid"], 2)
        },
        "per_full_month": {
            "kwh": round(-per_day * 30, 2),
            "cost_rs": round(
                new["cost_rs"]["mid"] - base["cost_rs"]["mid"], 2
            )
        },
        "formula": spec["formula"],
        "assumptions": assumptions,
        "limits": (
            "A plan is not a measured saving. "
            "The whole CEB tariff is recalculated, not an average price."
        )
    }


def unusual_usage(state):
    periods = measured_periods(state)

    if len(periods) < 3:
        return None

    def daily_rate(period):
        days = max((period["end"] - period["start"]).days, 1)
        return period["kwh"] / days

    latest = daily_rate(periods[-1])
    usual = sum(
        daily_rate(p) for p in periods[:-1]
    ) / (len(periods) - 1)

    if usual <= 0 or latest < UNUSUAL_RATIO * usual:
        return None

    return {
        "latest_kwh_per_day": round(latest, 2),
        "usual_kwh_per_day": round(usual, 2),
        "increase_pct": round((latest / usual - 1) * 100),
        "period_start": periods[-1]["start"].isoformat(),
        "period_end": periods[-1]["end"].isoformat()
    }


def _budget(state, f):
    budget = state.get("profile", {}).get("monthly_budget_rs")

    if not budget or f.get("status") != "ok":
        return None

    status = (
        "over" if f["cost_rs"]["mid"] > budget
        else "at_risk" if f["cost_rs"]["high"] > budget
        else "ok"
    )

    return {
        "budget_rs": budget,
        "projected_rs": f["cost_rs"]["mid"],
        "high_rs": f["cost_rs"]["high"],
        "status": status
    }


def insights(state):
    f = forecast(state)

    out = {
        "module": "electricity",
        "forecast": f,
        "recommendations": [],
        "benchmark": None,
        "budget": None,
        "expected_use_change": (
            f.get("adjustments", {}).get("expected_use_change")
        )
    }

    if f.get("status") != "ok":
        return out

    month = f["daily_average_kwh"] * 30

    out["benchmark"] = {
        "you_kwh_per_month": round(month),
        "mauritius_kwh_per_month": MU_KWH_PER_MONTH,
        "difference_pct": round(
            (month / MU_KWH_PER_MONTH - 1) * 100
        ),
        "source": "Statistics Mauritius 2025, domestic average per consumer"
    }

    out["budget"] = _budget(state, f)

    evidence = {
        "period_start": f["period_start"],
        "period_end": f["period_end"],
        "projected_kwh": f["kwh"]["mid"],
        "method": f["method"],
        "source_data": f["source_data"]
    }

    # E5 expected usage adjustment.
    e5 = out["expected_use_change"]

    if e5 and e5["status"] in ("applied", "needs_input"):
        out["recommendations"].append({
            "id": "expected_usage_change",
            "kind": "information",
            "title": "Expected usage change",
            "detail": e5["message"],
            "evidence": {**evidence, **e5}
        })

    jump = unusual_usage(state)

    if jump:
        out["recommendations"].append({
            "id": "unusual_usage",
            "kind": "alert",
            "title": (
                f"Electricity use is {jump['increase_pct']}% "
                "above your usual"
            ),
            "detail": (
                "Check what changed: a new appliance, more air conditioning, "
                "or a water heater left on."
            ),
            "evidence": {**evidence, **jump}
        })

    if out["budget"] and out["budget"]["status"] != "ok":
        budget = out["budget"]

        out["recommendations"].append({
            "id": "budget",
            "kind": "alert",
            "title": (
                "Over your electricity budget"
                if budget["status"] == "over"
                else "Could go over your electricity budget"
            ),
            "detail": (
                f"Projected Rs {budget['projected_rs']:.0f} "
                f"(up to Rs {budget['high_rs']:.0f}) "
                f"vs your budget of Rs {budget['budget_rs']:.0f}."
            ),
            "evidence": {**evidence, **budget}
        })

    completed = {
        a["key"]: a for a in state.get("actions", [])
    }

    ranked = []

    for key, params in _eligible_actions(state):
        result = scenario(state, key, params)

        if result["status"] == "ok":
            ranked.append(result)

    ranked.sort(
        key=lambda result: result["per_full_month"]["cost_rs"]
    )

    for result in ranked:
        action = completed.get(result["action"])

        out["recommendations"].append({
            "id": result["action"] + "_" + str(
                result["params"].get("appliance", "general")
            ),
            "kind": "action",
            "title": result["title"],
            "detail": (
                f"Saves about "
                f"{abs(result['per_full_month']['kwh']):g} kWh "
                f"and Rs {abs(result['per_full_month']['cost_rs']):.0f} a month."
            ),
            "status": action["status"] if action else "suggested",
            "saving": {
                "kwh": abs(result["per_full_month"]["kwh"]),
                "cost_rs": abs(result["per_full_month"]["cost_rs"]),
                "per": "month"
            },
            "evidence": {
                key: result[key]
                for key in (
                    "period_start",
                    "period_end",
                    "baseline",
                    "with_action",
                    "difference",
                    "per_full_month",
                    "formula",
                    "assumptions",
                    "params",
                    "limits",
                    "power_estimated"
                )
            }
        })

    return out


def summary(state):
    """Shared module contract consumed by Household AI."""

    insights_data = insights(state)
    f = insights_data["forecast"]

    recent_activity = list(
        reversed(state.get("activity", []))
    )[:10]

    if f.get("status") != "ok":
        return {
            "module": "electricity",
            "status": "no_data",
            "currency": "MUR",
            "forecast_status": f.get(
                "forecast_status", "insufficient_data"
            ),
            "message": f.get(
                "message",
                "Add a confirmed electricity bill or sufficient meter readings to generate a forecast."
            ),
            "recent_activity": recent_activity
        }

    return {
        "module": "electricity",
        "status": "ok",
        "currency": "MUR",
        "period_start": f["period_start"],
        "period_end": f["period_end"],
        "forecast_status": f["forecast_status"],
        "forecast": {
            "amount": f["kwh"]["mid"],
            "unit": "kWh",
            "low": f["kwh"]["low"],
            "high": f["kwh"]["high"],
            "cost_rs": f["cost_rs"]["mid"],
            "cost_low_rs": f["cost_rs"]["low"],
            "cost_high_rs": f["cost_rs"]["high"],
            "confidence": f["confidence"],
            "method": f["method"],
            "adjustments": f.get("adjustments", {})
        },
        "benchmark": insights_data["benchmark"],
        "budget": insights_data["budget"],
        "context": {
            "expected_use_change": insights_data["expected_use_change"]
        },
        "recommendations": [
            {
                "id": recommendation["id"],
                "kind": recommendation["kind"],
                "title": recommendation["title"],
                "detail": recommendation["detail"],
                "saving": recommendation.get("saving"),
                "status": recommendation.get("status"),
                "evidence": recommendation["evidence"]
            }
            for recommendation in insights_data["recommendations"]
        ],
        "recent_activity": recent_activity
    }
