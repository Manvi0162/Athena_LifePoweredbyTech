"""Billing-cycle forecast (deterministic, explainable).

  observed  = units already used in the current cycle (daily history)
  daily     = average of the last 30 days
  projected = observed + daily x days left in the cycle
  range     = the same projection using the 10th and 90th percentile of 30-day averages
              (re-sampled from recent days with a fixed seed)
  cost      = the official tariff applied to projected units (rising blocks)
Every result returns its period, method, assumptions and source data, so the UI can explain it.
"""
import random
from datetime import date, timedelta

from . import tariffs
from .history import daily_history

CYCLE_DAYS = 30


def _bill(utility, units, days, household):
    if utility == "water":
        return tariffs.water_bill(units, days, sewer=household.get("sewer", False))
    return tariffs.electricity_bill(units, days, tariff_code=household.get("ceb_tariff", "120"),
                                    tv_licence=household.get("tv_licence", True))


def current_cycle(household, utility):
    bills = sorted((b for b in household["bills"] if b["utility"] == utility), key=lambda b: b["end"])
    today = date.fromisoformat(household["today"])
    start = date.fromisoformat(bills[-1]["end"]) if bills else today
    while start + timedelta(CYCLE_DAYS) <= today:        # several cycles since the last bill: move to the open one
        start += timedelta(CYCLE_DAYS)
    return start, start + timedelta(CYCLE_DAYS)


def forecast(household, utility, extra_saving_per_day=0.0):
    hist = daily_history(household, utility)
    if not hist:
        return {"utility": utility, "status": "no_data", "message": f"Add at least one {utility} bill to get a forecast."}
    start, end = current_cycle(household, utility)
    today = date.fromisoformat(household["today"])
    so_far = [h for h in hist if start <= date.fromisoformat(h["date"]) <= today]
    observed = sum(h["units"] for h in so_far)
    left = max((end - today).days - 1, 0)
    recent = [h["units"] for h in hist[-30:]]
    daily = sum(recent) / len(recent) - extra_saving_per_day
    rnd = random.Random(f"{household.get('seed', 'demo')}-{utility}-range")
    means = sorted(sum(rnd.choice(recent) for _ in range(30)) / 30 for _ in range(400))
    lo, hi = means[40] - extra_saving_per_day, means[360] - extra_saving_per_day
    units = {k: round(max(observed + max(v, 0) * left, 0), 2) for k, v in (("low", lo), ("mid", daily), ("high", hi))}
    cost = {k: _bill(utility, v, CYCLE_DAYS, household).total for k, v in units.items()}
    n_bills = sum(1 for b in household["bills"] if b["utility"] == utility)
    unit = "m3" if utility == "water" else "kWh"
    blocks = tariffs.WATER_BLOCKS if utility == "water" else tariffs.ELECTRICITY_BLOCKS
    return {
        "utility": utility, "status": "ok", "unit": unit, "currency": "MUR",
        "period_start": start.isoformat(), "period_end": end.isoformat(), "days_so_far": len(so_far), "days_left": left,
        "observed_units": round(observed, 2), "daily_average": round(daily, 3), "units": units, "cost_rs": cost,
        "bill_breakdown": _bill(utility, units["mid"], CYCLE_DAYS, household).as_dict(),
        "block": tariffs.next_block(units["mid"], blocks),
        "method": "observed so far + 30-day daily average x days left; range from 10th-90th percentile of re-sampled 30-day averages",
        "assumptions": ["Daily values are synthetic, calibrated so each month equals the real bill",
                        f"Cycle length {CYCLE_DAYS} days from the last bill",
                        "Official tariff blocks applied per bill (see data/SOURCES.md)"],
        "source_data": {"real_bills": n_bills, "synthetic_days": sum(1 for h in hist if h["kind"] == "synthetic")},
        "confidence": "good" if n_bills >= 3 else "low" if n_bills <= 1 else "medium",
    }
