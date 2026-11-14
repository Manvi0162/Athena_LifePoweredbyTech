
"""Deterministic, explainable next-cycle electricity forecast."""

from datetime import timedelta
from statistics import mean

from . import tariff
from .history import d, measured_periods, today

CYCLE_DAYS = 30


def bill_for(state, kwh):
    profile = state.get("profile", {})
    return tariff.electricity_bill(
        kwh,
        tariff_code=profile.get("ceb_tariff", "140"),
        tv_licence=profile.get("tv_licence", True)
    )


def _confirmed_bills(state):
    return sorted(
        [
            b for b in state.get("bills", [])
            if b.get("source") != "placeholder"
            and float(b.get("kwh", 0)) > 0
            and (d(b["end"]) - d(b["start"])).days > 0
        ],
        key=lambda b: b["end"]
    )


def historical_backtests(state):
    """
    Backtest each bill using only the bills that came before it.
    These are historical estimates, not live forecasts.
    """
    bills = _confirmed_bills(state)
    checks = []

    for index in range(1, len(bills)):
        previous_bills = bills[:index]
        actual_bill = bills[index]

        previous_rates = []

        for bill in previous_bills:
            days = (d(bill["end"]) - d(bill["start"])).days
            if days > 0:
                previous_rates.append(float(bill["kwh"]) / days)

        if not previous_rates:
            continue

        actual_days = (
            d(actual_bill["end"]) - d(actual_bill["start"])
        ).days

        if actual_days <= 0:
            continue

        predicted_daily = mean(previous_rates)
        predicted_kwh = predicted_daily * actual_days
        actual_kwh = float(actual_bill["kwh"])

        predicted_cost = bill_for(state, predicted_kwh).total
        actual_cost = bill_for(state, actual_kwh).total

        error_kwh = predicted_kwh - actual_kwh
        error_pct = (
            abs(error_kwh) / actual_kwh * 100
            if actual_kwh > 0 else 0
        )

        checks.append({
            "kind": "backtest",
            "verified": True,
            "bill_id": actual_bill.get("id"),
            "period_start": actual_bill["start"],
            "period_end": actual_bill["end"],
            "predicted_kwh": round(predicted_kwh, 2),
            "actual_kwh": round(actual_kwh, 2),
            "error_kwh": round(error_kwh, 2),
            "error_pct": round(error_pct, 2),
            "predicted_cost_rs": round(predicted_cost, 2),
            "actual_cost_rs": round(actual_cost, 2),
            "error_rs": round(predicted_cost - actual_cost, 2),
            "training_bills": len(previous_bills)
        })

    return checks


def _forecast_period(state):
    bills = _confirmed_bills(state)

    if bills:
        start = d(bills[-1]["end"])
    else:
        readings = sorted(
            state.get("readings", []),
            key=lambda r: r["date"]
        )
        start = d(readings[-1]["date"]) if readings else today(state)

    return start, start + timedelta(days=CYCLE_DAYS)


def _daily_rates(state):
    """Calculate daily rates from real measured periods only."""
    periods = measured_periods(state)
    rates = []

    for period in periods:
        days = (period["end"] - period["start"]).days

        if days <= 0 or period["kwh"] < 0:
            continue

        rates.append({
            "start": period["start"],
            "end": period["end"],
            "daily": period["kwh"] / days,
            "kwh": period["kwh"],
            "days": days,
            "kind": period["kind"]
        })

    return rates


def _completed_adjustments(state, start, end):
    """Calculate daily savings from actions completed before the forecast cycle."""
    from .history import completed_savings

    adjustments = []

    for saving in completed_savings(state):
        effective_start = max(start, saving["from"])

        if effective_start >= end:
            continue

        days = (end - effective_start).days

        adjustments.append({
            "from": effective_start.isoformat(),
            "kwh_per_day": round(saving["kwh_per_day"], 4),
            "days": days,
            "total_kwh": round(saving["kwh_per_day"] * days, 2)
        })

    return adjustments


def _checked_forecasts(state):
    """Return saved checks that contain actual and predicted measurements."""
    return [
        check for check in state.get("forecast_checks", [])
        if check.get("verified") is True
        or (
            check.get("kind") == "forecast_checked"
            and check.get("actual_kwh") is not None
            and check.get("predicted_kwh") is not None
        )
    ]


def _forecast_status(bills, checks):
    if len(bills) >= 3 and len(checks) >= 2:
        return "better_supported"

    if len(bills) >= 1:
        return "preliminary"

    return "insufficient_data"


def save_forecast_snapshot(state, forecast_result):
    """Persist a snapshot of an issued forecast so later bills can be checked against it."""
    if forecast_result.get("status") != "ok":
        return None

    snapshot = {
        "kind": "forecast_snapshot",
        "snapshot_id": f"forecast-{len(state.get('forecast_history', [])) + 1}",
        "period_start": forecast_result["period_start"],
        "period_end": forecast_result["period_end"],
        "forecast_status": forecast_result.get("forecast_status", "preliminary"),
        "predicted_kwh": forecast_result["kwh"]["mid"],
        "predicted_cost_rs": forecast_result["cost_rs"]["mid"],
        "confidence": forecast_result.get("confidence", "low"),
        "created_at": today(state).isoformat(),
    }

    history = state.setdefault("forecast_history", [])
    if not any(
        item.get("period_start") == snapshot["period_start"]
        and item.get("period_end") == snapshot["period_end"]
        for item in history
    ):
        history.append(snapshot)

    return snapshot


def add_forecast_checks_for_bill(state, bill):
    """Create actual checked forecasts when a confirmed bill covers a saved forecast snapshot."""
    if not bill or not bill.get("kwh"):
        return []

    history = state.get("forecast_history", [])
    if not history:
        return []

    bill_start = d(bill["start"])
    bill_end = d(bill["end"])
    checks = []

    for snapshot in history:
        snapshot_start = d(snapshot["period_start"])
        snapshot_end = d(snapshot["period_end"])
        if bill_end < snapshot_start or bill_start > snapshot_end:
            continue

        predicted_kwh = float(snapshot.get("predicted_kwh", 0.0))
        actual_kwh = float(bill.get("kwh", 0.0))
        error_kwh = predicted_kwh - actual_kwh
        error_pct = abs(error_kwh) / actual_kwh * 100 if actual_kwh > 0 else 0.0
        predicted_cost = float(snapshot.get("predicted_cost_rs", bill_for(state, predicted_kwh).total))
        actual_cost = bill_for(state, actual_kwh).total

        check = {
            "kind": "forecast_checked",
            "verified": True,
            "snapshot_id": snapshot.get("snapshot_id"),
            "period_start": snapshot["period_start"],
            "period_end": snapshot["period_end"],
            "actual_kwh": round(actual_kwh, 2),
            "predicted_kwh": round(predicted_kwh, 2),
            "error_kwh": round(error_kwh, 2),
            "error_pct": round(error_pct, 2),
            "actual_cost_rs": round(actual_cost, 2),
            "predicted_cost_rs": round(predicted_cost, 2),
            "error_rs": round(predicted_cost - actual_cost, 2),
            "bill_id": bill.get("id"),
        }

        existing = state.setdefault("forecast_checks", [])
        if not any(
            item.get("snapshot_id") == check["snapshot_id"] and item.get("bill_id") == check["bill_id"]
            for item in existing
        ):
            existing.append(check)
            checks.append(check)

    return checks


def _has_assessment_answer(value):
    """Check whether an assessment question has a meaningful answer."""
    if value is None:
        return False

    if isinstance(value, str):
        cleaned = value.strip().lower()
        return cleaned not in (
            "", "not sure", "not_sure", "notsure", "unsure", "unknown"
        )

    if isinstance(value, (list, tuple, set)):
        return any(
            _has_assessment_answer(item)
            for item in value
        )

    return True


def _data_completeness(state, bills):
    """
    Completeness measures how much household information is available.
    It does not affect forecast reliability.
    """
    # Five possible bill fields.
    bill_fields = ("start", "end", "kwh", "amount_rs", "tariff_class")
    latest_bill = bills[-1] if bills else {}

    known_bill_fields = 0

    for field in bill_fields:
        value = latest_bill.get(field)

        if field == "tariff_class" and not value:
            value = state.get("profile", {}).get("ceb_tariff")

        if value is not None and value != "":
            known_bill_fields += 1

    # Five assessment answers.
    assessment = state.get("assessment", {}) or {}

    assessment_fields = (
        ("appliances", "E1"),
        ("ac_hours", "E2"),
        ("water_heating", "E3"),
        ("cooking_energy", "E4"),
        ("expected_use", "E5")
    )

    answered_questions = 0

    for primary, fallback in assessment_fields:
        value = assessment.get(primary, assessment.get(fallback))

        if _has_assessment_answer(value):
            answered_questions += 1

    # One additional point for a current-cycle meter reading.
    readings = state.get("readings", [])
    latest_bill_end = (
        d(bills[-1]["end"]) if bills else None
    )

    has_current_reading = any(
        d(reading["date"]) >= latest_bill_end
        if latest_bill_end
        else True
        for reading in readings
        if reading.get("date")
    )

    total_known = (
        known_bill_fields
        + answered_questions
        + int(has_current_reading)
    )

    total_possible = 11

    return {
        "score": round(total_known / total_possible * 100),
        "known_bill_fields": known_bill_fields,
        "total_bill_fields": 5,
        "answered_assessment_questions": answered_questions,
        "total_assessment_questions": 5,
        "has_current_cycle_reading": has_current_reading
    }


def confidence(state, status):
    """Confidence is based on measured evidence and verified forecast checks."""
    if status == "better_supported":
        return "good"

    if status == "preliminary":
        return "medium"

    return "low"

def _expected_use_adjustment(state, baseline_kwh):
    """Apply E5 only when the user supplies a measurable change."""
    assessment = state.get("assessment", {}) or {}

    direction = assessment.get(
        "expected_use",
        assessment.get("E5")
    )

    if direction is None:
        return {
            "status": "not_answered",
            "delta_kwh": 0.0,
            "message": "Answer Electricity question 5 if you want to include an expected usage change."
        }

    direction = str(direction).strip().lower()

    if direction in ("no", "none", "no change"):
        return {
            "status": "no_change",
            "delta_kwh": 0.0,
            "message": "No expected usage change."
        }

    if direction in ("not_sure", "not sure", "unsure"):
        return {
            "status": "not_sure",
            "delta_kwh": 0.0,
            "message": "No adjustment applied because the expected change is unknown."
        }

    if direction not in ("increase", "decrease"):
        return {
            "status": "needs_input",
            "delta_kwh": 0.0,
            "message": "Answer Electricity question 5 with no change, increase, decrease or not sure."
        }

    amount_kwh = assessment.get("expected_change_kwh")
    amount_pct = assessment.get("expected_change_pct")

    if amount_kwh is None and amount_pct is None:
        return {
            "status": "needs_input",
            "delta_kwh": 0.0,
            "message": (
                "You selected an expected usage change. "
                "Please enter the estimated change in kWh or percentage."
            )
        }

    try:
        if amount_kwh is not None:
            amount = float(amount_kwh)

            if not 0 < amount <= 100000:
                raise ValueError

            delta = amount
            unit = "kWh"

        else:
            amount = float(amount_pct)

            if not 0 < amount <= 100:
                raise ValueError

            delta = baseline_kwh * amount / 100
            unit = "%"

    except (TypeError, ValueError):
        return {
            "status": "needs_input",
            "delta_kwh": 0.0,
            "message": "Enter a valid positive usage change."
        }

    if direction == "decrease":
        delta = -delta

    return {
        "status": "applied",
        "direction": direction,
        "input_value": amount,
        "input_unit": unit,
        "delta_kwh": round(delta, 2),
        "message": (
            f"Expected usage {direction}: "
            f"{amount:g} {unit} per billing cycle."
        )
    }

def forecast(state, extra_saving_per_day=0.0):
    bills = _confirmed_bills(state)
    rates = _daily_rates(state)

    # Separate historical backtests from actual checked forecasts.
    backtests = historical_backtests(state)
    saved_checks = _checked_forecasts(state)
    data_completeness = _data_completeness(state, bills)

    status = _forecast_status(bills, saved_checks)
    checks = saved_checks

    if not rates:
        return {
            "module": "electricity",
            "status": "insufficient_data",
            "forecast_status": "insufficient_data",
            "message": (
                "Add a confirmed electricity bill or at least "
                "two meter readings to get a forecast."
            ),
            "confidence": "low",
            "data_completeness": data_completeness,
        }

    start, end = _forecast_period(state)

    latest = rates[-1]

    if latest["kind"] == "reading" and latest["days"] >= 5:
        daily_baseline = latest["daily"]
        basis_label = (
            f"latest meter-reading period "
            f"({latest['start']} to {latest['end']})"
        )
    else:
        recent = rates[-30:]
        daily_baseline = mean(item["daily"] for item in recent)
        basis_label = "average of the latest measured periods"

    adjustments = _completed_adjustments(state, start, end)

    total_action_saving = sum(
        item["total_kwh"] for item in adjustments
    )

    days = (end - start).days
    baseline_kwh = daily_baseline * days

    e5_adjustment = _expected_use_adjustment(state, baseline_kwh)
    e5_delta = e5_adjustment["delta_kwh"]

    scenario_saving = max(float(extra_saving_per_day), 0.0) * days

    projected_kwh = max(
        baseline_kwh
        - total_action_saving
        - scenario_saving
        + e5_delta,
        0.0
    )

    measured_rates = [item["daily"] for item in rates[-30:]]
    low_daily = min(measured_rates)
    high_daily = max(measured_rates)

    low_kwh = max(
        low_daily * days
        - total_action_saving
        - scenario_saving
        + e5_delta,
        0.0
    )

    high_kwh = max(
        high_daily * days
        - total_action_saving
        - scenario_saving
        + e5_delta,
        0.0
    )

    kwh = {
        "low": round(min(low_kwh, projected_kwh), 2),
        "mid": round(projected_kwh, 2),
        "high": round(max(high_kwh, projected_kwh), 2)
    }

    costs = {
        key: round(bill_for(state, value).total, 2)
        for key, value in kwh.items()
    }

    # MAPE: mean ABSOLUTE percentage error (a signed mean would let +10% and -10% cancel out to 0%).
    # Uses the real checked forecasts and the historical backtests (each bill predicted from earlier bills only).
    _errors = [abs(c["error_pct"]) for c in list(checks) + list(backtests) if c.get("error_pct") is not None]
    mean_absolute_error = round(mean(_errors), 2) if _errors else None

    return {
        "module": "electricity",
        "status": "ok",
        "forecast_status": status,
        "unit": "kWh",
        "currency": "MUR",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "days": days,
        "daily_baseline_kwh": round(daily_baseline, 4),
        "daily_average_kwh": round(daily_baseline, 4),
        "kwh": kwh,
        "cost_rs": costs,
        "bill_breakdown": bill_for(state, kwh["mid"]).as_dict(),
        "method": (
            f"Next-cycle forecast: {daily_baseline:.2f} kWh/day "
            f"x {days} days, using {basis_label}. "
            "Completed actions are shown as separate savings adjustments. "
            "Costs are recalculated using the CEB rising-block tariff."
        ),
        "assumptions": [
            "The forecast period is 30 days.",
            "Daily consumption is based on real measured bill or meter-reading periods.",
            "The range uses the minimum and maximum recent measured daily rates.",
            "Historical backtests predict each bill using earlier bills only.",
            "The forecast is an estimate, not a measured reading.",
            "Expected usage changes are applied only when the user provides a measurable amount or percentage."
        ],
        "adjustments": {
            "completed_actions": adjustments,
            "total_action_saving_kwh": round(total_action_saving, 2),
            "scenario_saving_kwh": round(scenario_saving, 2),
            "expected_use_change": e5_adjustment
        },
        "source_data": {
            "confirmed_bills": len(bills),
            "meter_readings": len(state.get("readings", [])),
            "measured_periods": len(rates),
            "forecast_checks": len(checks),
            "historical_backtests": len(backtests),
            "mean_absolute_error_pct": mean_absolute_error
        },
        "backtests": backtests,
        "confidence": confidence(state, status),
        "data_completeness": data_completeness,
    }
