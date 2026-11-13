"""The calculator must reproduce the real CWA bill and the official blocks."""
from water.tariff import next_block, water_bill


def test_real_cwa_bill_zero_m3():
    # real CWA bill: 0 m3 -> water Rs 45 (minimum) + meter rent Rs 10 + postal Rs 14 = Rs 69
    assert water_bill(0).total == 69.00


def test_rising_blocks():
    assert water_bill(10).lines[0][1] == 60.00          # 10 x 6
    assert water_bill(20).lines[0][1] == 140.00         # 10x6 + 10x8
    assert water_bill(24).lines[0][1] == 208.00         # + 4x17
    assert water_bill(60).lines[0][1] == 970.00         # 10x6 + 10x8 + 30x17 + 10x32


def test_minimum_charge_below_rs45():
    assert water_bill(5).lines[0][1] == 45.00           # 5 x 6 = 30 < 45


def test_wastewater_only_when_on_sewer():
    assert len(water_bill(15, sewer=False).lines) == 3
    on = {l["label"]: l["rs"] for l in water_bill(15, sewer=True).as_dict()["lines"]}
    assert on["Wastewater charges"] == 120.00            # 10x7.5 + 5x9


def test_next_block():
    nb = next_block(18)
    assert nb == {"price_now": 8.0, "m3_to_next_block": 2.0, "next_price": 17.0}
