"""The calculators must reproduce the team's real bills to the rupee."""
from utility_engine.tariffs import ELECTRICITY_BLOCKS, block_charge, electricity_bill, next_block, water_bill


def test_ceb_real_bill_145_kwh():
    # CEB bill, 28.08.26-28.09.26, tariff 140: 145 kWh -> consumption Rs 828.00, meter Rs 20, TV licence Rs 150, total Rs 998
    b = electricity_bill(145, days=31, tariff_code="140", tv_licence=True)
    lines = {x["label"]: x["rs"] for x in b.as_dict()["lines"]}
    assert round(lines["Consumption charges"]) == 828
    assert round(b.total) == 998


def test_cwa_real_bill_zero_m3():
    # CWA bill, Jul 2025: 0 m3 -> water Rs 45 (minimum), meter rent Rs 10, postal Rs 14, total Rs 69
    assert water_bill(0, days=30, sewer=False).total == 69.00


def test_water_blocks_rise():
    assert water_bill(10).lines[0][1] == 60.00                  # 10 x 6
    assert water_bill(20).lines[0][1] == 140.00                 # 10x6 + 10x8
    assert water_bill(25).lines[0][1] == 225.00                 # + 5x17


def test_block_pro_rata_for_longer_period():
    month, _ = block_charge(120, ELECTRICITY_BLOCKS, 30, prorate=True)
    longer, _ = block_charge(120, ELECTRICITY_BLOCKS, 36, prorate=True)   # optional what-if only
    assert longer < month


def test_next_block_warning():
    nb = next_block(18, [(0, 10, 6.0), (10, 20, 8.0), (20, 50, 17.0), (50, None, 32.0)])
    assert nb["price_now"] == 8.0 and nb["units_to_next_block"] == 2 and nb["next_price"] == 17.0
