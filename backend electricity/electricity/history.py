
import random
from datetime import date, timedelta

WEEKEND_FACTOR = 1.10
NOISE_SD = 0.12
MIN_READING_DAYS = 5


def d(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def today(state):
    return d(state.get("today") or date.today())


def _shape(day, rnd):
    weekday_factor = WEEKEND_FACTOR if day.weekday() >= 5 else 1.0
    return weekday_factor * max(0.4, rnd.gauss(1.0, NOISE_SD))


def measured_periods(state):
    """Return real measured periods, oldest first."""
    bills = sorted(state.get("bills", []), key=lambda b: b["start"])

    periods = [
        {
            "start": d(b["start"]),
            "end": d(b["end"]),
            "kwh": float(b["kwh"]),
            "kind": "bill"
        }
        for b in bills
    ]

    last_bill = bills[-1] if bills else None
    last_end = d(last_bill["end"]) if last_bill else None

    points = []

    if last_bill and last_bill.get("end_reading") is not None:
        points.append((last_end, float(last_bill["end_reading"])))

    readings = sorted(
        (
            (d(r["date"]), float(r["index_kwh"]))
            for r in state.get("readings", [])
            if last_end is None or d(r["date"]) > last_end
        ),
        key=lambda item: item[0]
    )

    points.extend(readings)

    for (start, previous), (end, current) in zip(points, points[1:]):
        if end > start:
            periods.append({
                "start": start,
                "end": end,
                "kwh": current - previous,
                "kind": "reading"
            })

    return sorted(periods, key=lambda p: p["start"])


def _split(periods, rnd):
    """Create estimated daily values while preserving each measured total."""
    days = []

    for period in periods:
        span_days = (period["end"] - period["start"]).days

        if span_days <= 0:
            continue

        dates = [
            period["start"] + timedelta(days=i)
            for i in range(span_days)
        ]

        weights = [_shape(day, rnd) for day in dates]
        total_weight = sum(weights)

        if total_weight <= 0:
            continue

        exact_values = [
            period["kwh"] * weight / total_weight
            for weight in weights
        ]

        # Round daily values but preserve the exact measured total.
        rounded_values = [
            round(value, 4) for value in exact_values
        ]

        difference = round(period["kwh"] - sum(rounded_values), 4)
        rounded_values[-1] = round(rounded_values[-1] + difference, 4)

        for day, value in zip(dates, rounded_values):
            days.append({
                "date": day.isoformat(),
                "kwh": value,
                "kind": period["kind"],
                "measured": False,
                "saved": 0.0
            })

    return days


def basis(state):
    """Return estimated daily values from measured periods for forecasting."""
    periods = measured_periods(state)

    if not periods:
        return [], "none"

    days = _split(
        periods,
        random.Random(f"{state.get('seed', 'demo')}-electricity")
    )

    if not days:
        return [], "none"

    last = periods[-1]

    if (
        last["kind"] == "reading"
        and (last["end"] - last["start"]).days >= MIN_READING_DAYS
    ):
        count = (last["end"] - last["start"]).days
        return (
            [item["kwh"] for item in days[-count:]],
            f"meter readings {last['start']} to {last['end']}"
        )

    return (
        [item["kwh"] for item in days[-30:]],
        "last 30 measured days (estimated daily split)"
    )


def completed_savings(state):
    """Return completed action savings as separate dated adjustments."""
    from .actions import saving_per_day

    profile = state.get("profile", {})
    savings = []

    for action in state.get("actions", []):
        if action.get("status") != "completed":
            continue

        savings.append({
            "from": d(action["completed_on"]),
            "kwh_per_day": saving_per_day(
                action["key"],
                action.get("params", {}),
                profile
            )
        })

    return savings


def daily_history(state, until=None):
    """
    Return daily history.

    Bill and reading periods have estimated daily splits whose totals
    preserve measured kWh exactly. Days after the last measurement
    are synthetic estimates, not real meter readings.
    """
    until = d(until or today(state))
    periods = measured_periods(state)

    if not periods:
        return []

    rnd = random.Random(f"{state.get('seed', 'demo')}-electricity")
    output = _split(periods, rnd)

    values, _ = basis(state)

    if not values:
        return output

    daily_baseline = sum(values) / len(values)
    measured_until = periods[-1]["end"]

    savings = [
        item for item in completed_savings(state)
        if item["from"] >= measured_until
    ]

    day = measured_until

    while day <= until:
        saved = sum(
            item["kwh_per_day"]
            for item in savings
            if item["from"] <= day
        )

        estimated = daily_baseline * _shape(day, rnd)

        output.append({
            "date": day.isoformat(),
            "kwh": round(max(estimated - saved, 0.0), 4),
            "kind": "synthetic",
            "measured": False,
            "saved": round(saved, 4)
        })

        day += timedelta(days=1)

    return output
