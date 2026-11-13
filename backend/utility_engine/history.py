"""Daily usage history: REAL bill totals, SYNTHETIC day-by-day split (clearly labelled).

Why: bills give one number per month. Forecasts, trends and "what changed after you acted" need daily values.
How:
  1. For every real bill period, make one value per day with a weekday pattern + small random variation
     (fixed seed, so the demo is repeatable).
  2. Scale the days so they add up EXACTLY to the bill (the real data is never changed).
  3. After the last bill, continue at the household's recent average (synthetic, until the next real bill).
  4. Actions the household completed (e.g. shorter showers) reduce the synthetic days from that date on.
"""
import random
from datetime import date, timedelta

WEEKEND = {"water": 1.12, "electricity": 1.10}    # more people at home on Sat/Sun
NOISE = 0.12                                      # day-to-day variation (~12%)


def _d(x):
    return x if isinstance(x, date) else date.fromisoformat(x)


def _shape(day, utility, rnd):
    w = WEEKEND[utility] if day.weekday() >= 5 else 1.0
    return w * max(0.4, rnd.gauss(1.0, NOISE))


def daily_history(household, utility, until=None):
    """[{date, units, kind: 'bill' | 'synthetic', saved}] from the first bill to `until` (default: today)."""
    until = _d(until or household["today"])
    bills = sorted((b for b in household["bills"] if b["utility"] == utility), key=lambda b: b["start"])
    if not bills:
        return []
    rnd = random.Random(f"{household.get('seed', 'demo')}-{utility}")
    out = []
    for b in bills:                                           # 1-2: split each real bill over its days
        s, e = _d(b["start"]), _d(b["end"])
        days = [s + timedelta(i) for i in range((e - s).days)]
        w = [_shape(d, utility, rnd) for d in days]
        k = b["units"] / sum(w) if sum(w) else 0
        out += [{"date": d.isoformat(), "units": round(x * k, 3), "kind": "bill", "saved": 0.0} for d, x in zip(days, w)]
    recent = [x["units"] for x in out[-60:]]                  # 3: continue at the recent average
    base = sum(recent) / len(recent) if recent else 0.0
    d = _d(bills[-1]["end"])
    savings = action_savings(household, utility)
    while d <= until:
        v = base * _shape(d, utility, rnd)
        saved = sum(s["units_per_day"] for s in savings if s["from"] <= d)   # 4: completed actions
        out.append({"date": d.isoformat(), "units": round(max(v - saved, 0.0), 3), "kind": "synthetic", "saved": round(saved, 3)})
        d += timedelta(1)
    return out


def action_savings(household, utility):
    from .actions import saving_per_day
    out = []
    for a in household.get("actions", []):
        if a["utility"] == utility and a["status"] == "completed":
            out.append({"from": _d(a["completed_on"]), "units_per_day": saving_per_day(a["key"], a.get("params", {}), household)})
    return out
