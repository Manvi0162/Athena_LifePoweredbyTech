"""Daily water history: REAL measured totals, SYNTHETIC day-by-day split (clearly labelled).

Why: a CWA bill gives one number per month. Forecasts, trends and "what changed after you acted" need days.

Measured periods (real numbers, never changed):
  - each bill:            start -> end, m3 from the bill
  - each meter reading:   previous reading (or the last bill's end reading) -> this reading, m3 = difference
How the days are made:
  1. Inside every measured period, one value per day = weekday pattern (weekends x1.12) x random variation
     (Gaussian, sd 12%, fixed seed so the demo is repeatable).
  2. The days are scaled so they add up EXACTLY to the measured m3.
  3. After the last measurement, days continue at the latest rate: the latest meter-reading period if it is
     at least 5 days long, otherwise the average of the last 30 measured days.
  4. Actions completed after the last measurement lower those continued days by their saving.
     (Actions completed earlier are already inside the measured numbers, so they are not subtracted twice.)
"""
import random
from datetime import date, timedelta

WEEKEND_FACTOR = 1.12
NOISE_SD = 0.12
MIN_READING_DAYS = 5


def d(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


def today(state):
    return d(state.get("today") or date.today())


def _shape(day, rnd):
    w = WEEKEND_FACTOR if day.weekday() >= 5 else 1.0
    return w * max(0.4, rnd.gauss(1.0, NOISE_SD))


def measured_periods(state):
    """Real measured periods, oldest first: [{start, end, m3, kind: 'bill' | 'reading'}]."""
    bills = sorted(state.get("bills", []), key=lambda b: b["start"])
    out = [{"start": d(b["start"]), "end": d(b["end"]), "m3": float(b["m3"]), "kind": "bill"} for b in bills]
    last_end = d(bills[-1]["end"]) if bills else None
    points = []
    if bills and bills[-1].get("end_reading") is not None:
        points.append((last_end, float(bills[-1]["end_reading"])))
    points += sorted((d(r["date"]), float(r["index_m3"])) for r in state.get("readings", [])
                     if last_end is None or d(r["date"]) > last_end)
    for (a, ia), (b, ib) in zip(points, points[1:]):
        if b > a:
            out.append({"start": a, "end": b, "m3": ib - ia, "kind": "reading"})
    return out


def _split(periods, rnd):
    days = []
    for p in periods:
        span = [p["start"] + timedelta(i) for i in range((p["end"] - p["start"]).days)]
        w = [_shape(x, rnd) for x in span]
        k = p["m3"] / sum(w) if sum(w) else 0.0
        days += [{"date": x.isoformat(), "m3": round(v * k, 4), "kind": p["kind"], "saved": 0.0} for x, v in zip(span, w)]
    return days


def basis(state):
    """Daily values the forecast extends from, and a label saying which ones."""
    periods = measured_periods(state)
    days = _split(periods, random.Random(f"{state.get('seed', 'demo')}-water"))
    if not days:
        return [], "none"
    last = periods[-1]
    if last["kind"] == "reading" and (last["end"] - last["start"]).days >= MIN_READING_DAYS:
        n = (last["end"] - last["start"]).days
        return [x["m3"] for x in days[-n:]], f"meter readings {last['start']} to {last['end']}"
    return [x["m3"] for x in days[-30:]], "last 30 measured days"


def completed_savings(state):
    from .actions import saving_per_day
    profile = state.get("profile", {})
    return [{"from": d(a["completed_on"]), "m3_per_day": saving_per_day(a["key"], a.get("params", {}), profile)}
            for a in state.get("actions", []) if a["status"] == "completed"]


def daily_history(state, until=None):
    """[{date, m3, kind: bill | reading | synthetic, saved}] from the first measurement to `until` (default today)."""
    until = d(until or today(state))
    periods = measured_periods(state)
    if not periods:
        return []
    rnd = random.Random(f"{state.get('seed', 'demo')}-water")
    out = _split(periods, rnd)
    values, _ = basis(state)
    base = sum(values) / len(values)
    measured_until = periods[-1]["end"]
    savings = [s for s in completed_savings(state) if s["from"] >= measured_until]
    day = measured_until
    while day <= until:
        saved = sum(s["m3_per_day"] for s in savings if s["from"] <= day)
        v = base * _shape(day, rnd)
        out.append({"date": day.isoformat(), "m3": round(max(v - saved, 0.0), 4), "kind": "synthetic", "saved": round(saved, 4)})
        day += timedelta(1)
    return out
