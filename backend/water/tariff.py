"""CWA domestic water tariff turned into a bill calculator.

RISING BLOCKS: each price applies only to the m3 inside its block (per monthly bill):
  first 10 m3 at Rs 6, next 10 at Rs 8, next 30 at Rs 17, above 50 at Rs 32.
  Example: 24 m3 = 10x6 + 10x8 + 4x17 = Rs 208.
If the block charge is below Rs 45 the minimum monthly charge (Rs 45) is billed instead.
Wastewater (only homes on the public sewer) has its own blocks and a Rs 55 minimum.
Fixed lines (meter rent, postal) are read from our real CWA bill.
Checked on the real bill: 0 m3 -> Rs 45 + 10 + 14 = Rs 69.
"""
import csv
import os
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(__file__), "data")


def _blocks(price_col):
    out = []
    with open(os.path.join(DATA, "cwa_domestic_tariff_2012.csv")) as fh:
        for r in csv.DictReader(fh):
            hi = r["block_to_m3_per_month"]
            out.append((float(r["block_from_m3_per_month"]), float(hi) if hi else None, float(r[price_col])))
    return out


BLOCKS = _blocks("potable_rs_per_m3")
WASTEWATER_BLOCKS = _blocks("wastewater_rs_per_m3")

MINIMUM = 45.00              # real CWA bill: 0 m3 billed Rs 45 "Water Charges"; Proag (2014) Tableau 3
WASTEWATER_MINIMUM = 55.00   # Proag (2014) Tableau 3
METER_RENT = 10.00           # real CWA bill (12 mm meter)
POSTAL = 14.00               # real CWA bill
# VAT: none on the domestic CWA bill.


@dataclass
class Bill:
    m3: float
    lines: list = field(default_factory=list)        # [(label, rupees, how)]

    @property
    def total(self):
        return round(sum(x[1] for x in self.lines), 2)

    def as_dict(self):
        return {"m3": round(self.m3, 2), "currency": "MUR", "total_rs": self.total,
                "lines": [{"label": a, "rs": round(b, 2), "how": c} for a, b, c in self.lines]}


def block_charge(m3, blocks=BLOCKS):
    """Rising-block charge. Returns (rupees, ['10 x Rs 6.00', ...]) so the bill can be explained."""
    rest, rupees, steps = max(m3, 0.0), 0.0, []
    for lo, hi, price in blocks:
        if rest <= 0:
            break
        take = rest if hi is None else min(rest, hi - lo)
        rupees += take * price
        steps.append(f"{take:g} x Rs {price:.2f}")
        rest -= take
    return round(rupees, 2), steps


def water_bill(m3, sewer=False):
    b = Bill(m3)
    charge, steps = block_charge(m3)
    b.lines.append(("Water charges", max(charge, MINIMUM),
                    "minimum monthly charge" if charge < MINIMUM else " + ".join(steps)))
    if sewer:
        ww, wsteps = block_charge(m3, WASTEWATER_BLOCKS)
        b.lines.append(("Wastewater charges", max(ww, WASTEWATER_MINIMUM),
                        "minimum monthly charge" if ww < WASTEWATER_MINIMUM else " + ".join(wsteps)))
    b.lines.append(("Meter rent", METER_RENT, "fixed"))
    b.lines.append(("Postal charges", POSTAL, "fixed"))
    return b


def next_block(m3, blocks=BLOCKS):
    """Current price per m3 and how many m3 are left before the price goes up."""
    for i, (lo, hi, price) in enumerate(blocks):
        if hi is None or m3 < hi:
            return {"price_now": price,
                    "m3_to_next_block": round(hi - m3, 2) if hi is not None else None,
                    "next_price": blocks[i + 1][2] if hi is not None else None}
    return None
