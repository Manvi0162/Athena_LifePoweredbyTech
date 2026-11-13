"""Official tariffs turned into bill calculators.

Both CWA (water) and CEB (electricity) use RISING BLOCKS: each price applies only to the units inside its
block. Example (CEB): 145 kWh = 25x3.63 + 25x5.04 + 25x5.45 + 25x6.27 + 45x7.07 = Rs 827.90 (bill: Rs 828).

Blocks are defined per month (per bill). The real CEB bill (31-day period, 145 kWh -> Rs 828) matches the
blocks WITHOUT scaling them for the 31 days, so by default blocks are not pro-rated. `prorate=True` is kept
for "what if the period were longer/shorter" questions.
Tariff values are loaded from backend/data/*.csv (see SOURCES.md).
"""
import csv
import os
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
MONTH_DAYS = 30.0


def _blocks(path, price_col):
    out = []
    with open(os.path.join(DATA, path)) as fh:
        for r in csv.DictReader(fh):
            lo = float(r[next(k for k in r if k.startswith("block_from"))])
            hi_raw = r[next(k for k in r if k.startswith("block_to"))]
            out.append((lo, float(hi_raw) if hi_raw else None, float(r[price_col])))
    return out


WATER_BLOCKS = _blocks("cwa_domestic_tariff_2012.csv", "potable_rs_per_m3")
WASTEWATER_BLOCKS = _blocks("cwa_domestic_tariff_2012.csv", "wastewater_rs_per_m3")
ELECTRICITY_BLOCKS = _blocks("ceb_domestic_tariff_2026.csv", "rs_per_kwh")
with open(os.path.join(DATA, "ceb_minimum_charge_2026.csv")) as _fh:
    CEB_MINIMUM = {r["tariff_code"]: float(r["minimum_monthly_charge_rs"]) for r in csv.DictReader(_fh)}

# Fixed amounts read from the team's real bills (Nov 2026); change them if a bill shows different values.
CWA_WATER_MINIMUM = 45.00          # CWA bill: 0 m3 charged Rs 45 "Water Charges"
CWA_WASTEWATER_MINIMUM = 55.00     # Proag (2014), Tableau 3
CWA_METER_RENT = 10.00             # CWA bill, 12 mm meter
CWA_POSTAL = 14.00                 # CWA bill
CEB_METER_RENT = 20.00             # CEB bill
CEB_TV_LICENCE = 150.00            # CEB bill (only homes that pay the TV licence)


@dataclass
class Bill:
    utility: str
    units: float
    unit_name: str
    days: int
    lines: list = field(default_factory=list)      # [(label, rupees, how)]

    @property
    def total(self):
        return round(sum(x[1] for x in self.lines), 2)

    def as_dict(self):
        return {"utility": self.utility, "units": round(self.units, 2), "unit": self.unit_name, "days": self.days,
                "lines": [{"label": a, "rs": round(b, 2), "how": c} for a, b, c in self.lines], "total_rs": self.total}


def block_charge(units, blocks, days=MONTH_DAYS, prorate=False):
    """Rising-block charge. Returns (rupees, [steps]) so every bill can be explained line by line."""
    scale = days / MONTH_DAYS if prorate else 1.0
    rest, rupees, steps = max(units, 0.0), 0.0, []
    for lo, hi, price in blocks:
        if rest <= 0:
            break
        size = (hi - lo) * scale if hi is not None else rest
        take = min(rest, size)
        rupees += take * price
        steps.append(f"{take:g} x Rs {price:.2f}")
        rest -= take
    return round(rupees, 2), steps


def water_bill(m3, days=30, sewer=False, meter_rent=CWA_METER_RENT, postal=CWA_POSTAL):
    b = Bill("water", m3, "m3", days)
    charge, steps = block_charge(m3, WATER_BLOCKS, days)
    if charge < CWA_WATER_MINIMUM:
        b.lines.append(("Water charges", CWA_WATER_MINIMUM, "minimum monthly charge"))
    else:
        b.lines.append(("Water charges", charge, " + ".join(steps)))
    if sewer:
        ww, wsteps = block_charge(m3, WASTEWATER_BLOCKS, days)
        b.lines.append(("Wastewater charges", max(ww, CWA_WASTEWATER_MINIMUM),
                        "minimum monthly charge" if ww < CWA_WASTEWATER_MINIMUM else " + ".join(wsteps)))
    b.lines.append(("Meter rent", meter_rent, "fixed"))
    b.lines.append(("Postal charges", postal, "fixed"))
    return b


def electricity_bill(kwh, days=30, tariff_code="140", tv_licence=True, meter_rent=CEB_METER_RENT):
    b = Bill("electricity", kwh, "kWh", days)
    charge, steps = block_charge(kwh, ELECTRICITY_BLOCKS, days)
    minimum = CEB_MINIMUM.get(str(tariff_code), 0.0)
    if charge < minimum:
        b.lines.append(("Consumption charges", minimum, f"minimum monthly charge, tariff {tariff_code}"))
    else:
        b.lines.append(("Consumption charges", charge, " + ".join(steps)))
    b.lines.append(("Meter rental", meter_rent, "fixed"))
    if tv_licence:
        b.lines.append(("TV licence fee", CEB_TV_LICENCE, "fixed"))
    b.lines.append(("VAT", 0.0, "domestic: 0 on the bill"))
    return b


def next_block(units, blocks):
    """The block the household is in and how many units are left before the price goes up."""
    scale = 1.0
    for lo, hi, price in blocks:
        if hi is None or units < hi * scale:
            nxt = next((p for (l2, h2, p) in blocks if l2 == hi), None) if hi is not None else None
            return {"price_now": price, "units_to_next_block": round(hi * scale - units, 2) if hi is not None else None,
                    "next_price": nxt}
    return None
