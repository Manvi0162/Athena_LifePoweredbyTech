"""Water bill forecast for the current billing cycle (deterministic and explainable).

  cycle      = 30 days starting at the last bill's end date (moved forward if several cycles have passed)
  observed   = m3 already used this cycle (meter readings where there are some, otherwise synthetic days)
  daily      = latest rate (latest meter-reading period, or the last 30 measured days) minus extra savings
  projected  = observed + daily x days left
  range      = same projection using the 10th and 90th percentile of 400 re-sampled 30-day averages
  cost       = the CWA tariff applied to the projected m3 (rising blocks, minimum, meter rent, postal)
Every result says its period, method, assumptions and source data, so the UI and the AI can explain it.
"""
import random
from datetime import timedelta

from . import tariff
from .history import basis, d, daily_history, today

CYCLE_DAYS = 30


def current_cycle(state):
    bills = sorted(state.get("bills", []), key=lambda b: b["end"])
    now = today(state)
    if bills:
        start = d(bills[-1]["end"])
    else:
        readings = sorted(state.get("readings", []), key=lambda r: r["date"])
        start = d(readings[0]["date"]) if readings else now
    while start + timedelta(CYCLE_DAYS) <= now:
        start += timedelta(CYCLE_DAYS)
    return start, start + timedelta(CYCLE_DAYS)


def bill_for(state, m3):
    return tariff.water_bill(m3, sewer=state.get("profile", {}).get("sewer", False))


def confidence(state, read_since_bill):
    """low / medium / good from the number of REAL bills, and whether the meter was read since the last bill."""
    real = sum(1 for b in state.get("bills", []) if b.get("source") != "placeholder")
    if real >= 3 or (real >= 1 and read_since_bill):
        return "good"
    if real == 2 or read_since_bill:
        return "medium"
    return "low"


def forecast(state, extra_saving_per_day=0.0):
    hist = daily_history(state)
    if not hist:
        return {"module": "water", "status": "no_data",
                "message": "Add a water bill (or two meter readings) to get a forecast."}
    start, end = current_cycle(state)
    now = today(state)
    so_far = [h for h in hist if start <= d(h["date"]) <= now]
    observed = sum(h["m3"] for h in so_far)
    metered = sum(h["m3"] for h in so_far if h["kind"] == "reading")
    left = max((end - now).days - 1, 0)
    values, basis_label = basis(state)
    daily = sum(values) / len(values) - extra_saving_per_day
    rnd = random.Random(f"{state.get('seed', 'demo')}-water-range")
    means = sorted(sum(rnd.choice(values) for _ in range(30)) / 30 for _ in range(400))
    rates = {"low": means[40], "mid": sum(values) / len(values), "high": means[360]}
    m3 = {k: round(max(observed + max(v - extra_saving_per_day, 0.0) * left, 0.0), 2) for k, v in rates.items()}
    cost = {k: bill_for(state, v).total for k, v in m3.items()}
    last_bill_end = max((b["end"] for b in state.get("bills", [])), default="")
    read_since_bill = any(r["date"] > last_bill_end for r in state.get("readings", []))
    placeholders = any(b.get("source") == "placeholder" for b in state.get("bills", []))
    return {
        "module": "water", "status": "ok", "unit": "m3", "currency": "MUR",
        "period_start": start.isoformat(), "period_end": end.isoformat(),
        "days_so_far": len(so_far), "days_left": left,
        "observed_m3": round(observed, 2), "observed_from_meter_m3": round(metered, 2),
        "daily_average_m3": round(daily, 4), "m3": m3, "cost_rs": cost,
        "bill_breakdown": bill_for(state, m3["mid"]).as_dict(),
        "block": tariff.next_block(m3["mid"]),
        "method": f"observed so far + daily rate ({basis_label}) x days left; "
                  "range = 10th-90th percentile of re-sampled 30-day averages; cost = CWA rising-block tariff",
        "assumptions": ["Daily values are synthetic, scaled so each bill / reading period equals the real m3",
                        f"Billing cycle of {CYCLE_DAYS} days from the last bill",
                        "CWA domestic tariff in force since 2012 (see data/SOURCES.md)"]
                       + (["Demo bills are placeholders until a real CWA bill is entered"] if placeholders else []),
        "source_data": {"real_bills": sum(1 for b in state.get("bills", []) if b.get("source") != "placeholder"),
                        "placeholder_bills": sum(1 for b in state.get("bills", []) if b.get("source") == "placeholder"),
                        "meter_readings": len(state.get("readings", [])),
                        "synthetic_days": sum(1 for h in hist if h["kind"] == "synthetic")},
        "confidence": confidence(state, read_since_bill),
    }
