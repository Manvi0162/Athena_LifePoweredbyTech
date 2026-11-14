"""CEB domestic electricity tariff (2026) turned into a bill calculator.

RISING BLOCKS: each price applies only to the kWh inside its block (per monthly bill), 12 blocks from Rs 3.63.
If the block charge is below the minimum for the household's tariff code (110 / 120 / 140), the minimum is billed.
Blocks are NOT scaled to the number of days: our real 31-day bill matches only without scaling.
Checked on the real CEB bill (tariff 140): 145 kWh = 25x3.63 + 25x5.04 + 25x5.45 + 25x6.27 + 45x7.07
  = Rs 827.90 (bill: Rs 828) + meter rental Rs 20 + TV licence Rs 150 = Rs 998.
"""
import csv
import os
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(__file__), "data")

with open(os.path.join(DATA, "ceb_domestic_tariff_2026.csv")) as _fh:
    BLOCKS = []
    for r in csv.DictReader(_fh):
        lo = float(r[next(k for k in r if k.startswith("block_from"))])
        hi = r[next(k for k in r if k.startswith("block_to"))]
        BLOCKS.append((lo, float(hi) if hi else None, float(r["rs_per_kwh"])))
with open(os.path.join(DATA, "ceb_minimum_charge_2026.csv")) as _fh:
    MINIMUM = {r["tariff_code"]: float(r["minimum_monthly_charge_rs"]) for r in csv.DictReader(_fh)}

METER_RENT = 20.00     # real CEB bill
TV_LICENCE = 150.00    # real CEB bill (only homes that pay the TV licence)
# VAT: 0 on the domestic CEB bill.


@dataclass
class Bill:
    kwh: float
    lines: list = field(default_factory=list)

    @property
    def total(self):
        return round(sum(x[1] for x in self.lines), 2)

    def as_dict(self):
        return {"kwh": round(self.kwh, 2), "currency": "MUR", "total_rs": self.total,
                "lines": [{"label": a, "rs": round(b, 2), "how": c} for a, b, c in self.lines]}


def block_charge(kwh, blocks=BLOCKS):
    rest, rupees, steps = max(kwh, 0.0), 0.0, []
    for lo, hi, price in blocks:
        if rest <= 0:
            break
        take = rest if hi is None else min(rest, hi - lo)
        rupees += take * price
        steps.append(f"{take:g} x Rs {price:.2f}")
        rest -= take
    return round(rupees, 2), steps


def electricity_bill(kwh, tariff_code="140", tv_licence=True):
    b = Bill(kwh)
    charge, steps = block_charge(kwh)
    minimum = MINIMUM.get(str(tariff_code), 0.0)
    b.lines.append(("Consumption charges", max(charge, minimum),
                    f"minimum monthly charge, tariff {tariff_code}" if charge < minimum else " + ".join(steps)))
    b.lines.append(("Meter rental", METER_RENT, "fixed"))
    if tv_licence:
        b.lines.append(("TV licence fee", TV_LICENCE, "fixed"))
    b.lines.append(("VAT", 0.0, "domestic: 0 on the bill"))
    return b


def next_block(kwh, blocks=BLOCKS):
    for i, (lo, hi, price) in enumerate(blocks):
        if hi is None or kwh < hi:
            return {"price_now": price, "kwh_to_next_block": round(hi - kwh, 2) if hi is not None else None,
                    "next_price": blocks[i + 1][2] if hi is not None else None}
    return None
