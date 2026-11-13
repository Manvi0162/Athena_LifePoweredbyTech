"""Forecast honesty rules from the 13 Nov spec."""
from water import assessment as A
from water import forecast as F
from water import seasonality as S
from datetime import date

from .conftest import ALL_ANSWERS


def test_no_bill_means_no_personal_forecast(empty):
    f = F.forecast(empty)
    assert f["status"] == "insufficient_data" and f["estimated_units"] is None and f["cost"] is None
    assert f["status_message"].startswith("Add your first bill")


def test_one_bill_gives_preliminary_period_normalised_estimate(one_bill):
    f = F.forecast(one_bill)
    assert f["status"] == "preliminary" and f["period"] == "next_30_day_cycle"
    obs = f["lines"][0]
    assert obs["kind"] == "observed" and abs(obs["m3"] - 18.0) < 1e-6          # 600 L/day x 30 days
    assert "one billing period" in f["status_message"] or "1 billing period" in f["status_message"]
    assert f["cost"]["note"].startswith("tariff_calculated_only")
    for k in ("kind", "period", "estimated_units", "units", "status", "method", "source_bill_count",
              "assessment_complete", "assumptions", "source_ids", "observed_vs_assumed"):
        assert k in f


def test_spec_example_18m3_30_days_to_31_days():
    bills = [{"id": "x", "start": "2026-06-01", "end": "2026-07-01", "m3": 18.0}]
    c = F.core(bills, {}, date(2026, 7, 1), 31)
    assert abs(c["baseline"] - 18.6) < 1e-9                                       # 600 L/day x 31


def test_lines_add_up_and_are_labelled(sample):
    f = F.forecast(sample)
    assert abs(sum(l["m3"] for l in f["lines"]) - f["estimated_units"]) < 0.02
    assert {l["kind"] for l in f["lines"]} <= {"observed", "data_adjustment", "user_declared", "action", "correction", "scenario"}


def test_assessment_raises_completeness_not_reliability(one_bill):
    before = F.forecast(one_bill)
    A.save_version(one_bill, ALL_ANSWERS)
    after = F.forecast(one_bill)
    assert after["data_completeness"]["pct"] > before["data_completeness"]["pct"]
    assert after["reliability"] == before["reliability"] and after["status"] == before["status"]
    assert after["estimated_units"] == before["estimated_units"]                  # answers are not consumption


def test_declared_change_is_its_own_line(one_bill):
    A.save_version(one_bill, {"W5_expected_change": "increase", "W5_change_pct": 10, "W5_reason": "guests"})
    f = F.forecast(one_bill)
    line = next(l for l in f["lines"] if l["kind"] == "user_declared")
    assert line["m3"] > 0 and "guests" in line["label"]


def test_declared_change_without_size_asks_for_it(one_bill):
    A.save_version(one_bill, {"W5_expected_change": "increase"})
    f = F.forecast(one_bill)
    assert not any(l["kind"] == "user_declared" for l in f["lines"])
    assert any("how much" in p for p in f["prompts"])


def test_three_bills_and_backtests_give_better_supported(sample):
    f = F.forecast(sample)
    assert f["status"] == "better_supported"
    assert f["reliability"]["backtests"] == 2 and f["reliability"]["mean_abs_error_pct"] is not None


def test_current_cycle_needs_readings(one_bill):
    assert F.current_cycle(one_bill)["status"] == "needs_readings"
    one_bill["readings"] = [{"id": "r1", "date": "2026-11-03", "index_m3": 1458.0}]
    c = F.current_cycle(one_bill)
    assert c["status"] == "measured_projection" and c["measured_rate_l_per_day"] == 381     # 8 m3 / 21 days


def test_season_factors_average_one_and_summer_higher():
    for region in ("Centre", "North"):
        p = {"region": region}
        f = [S.season_factor(date(2026, m, 15), p) for m in range(1, 13)]
        assert abs(sum(f) / 12 - 1) < 1e-9 and f[1] > 1 > f[6]
    assert S.season_factor(date(2026, 2, 15), {"has_air_conditioning": True}) < S.season_factor(date(2026, 2, 15), {})


def test_bill_vs_prediction_check(one_bill):
    snap = F.snapshot(one_bill, "test")
    new_bill = {"id": "b2", "start": "2026-10-13", "end": "2026-11-12", "m3": 20.0, "source": "confirmed"}
    one_bill["bills"].append(new_bill)
    chk = F.check_against_forecast(one_bill, new_bill)
    assert chk["forecast_id"] == snap["id"] and chk["actual_m3"] == 20.0 and chk["kind"] == "real"
    assert F.reliability(one_bill)["checked_forecasts"] == 1


def test_correction_is_visible_after_two_checks(sample, one_bill):
    assert not any(l["kind"] == "correction" for l in F.forecast(one_bill)["lines"])     # no checks yet
    corr = [l for l in F.forecast(sample)["lines"] if l["kind"] == "correction"]          # sample bills rise: we under-predict
    assert len(corr) == 1 and corr[0]["m3"] > 0 and "too low" in corr[0]["label"]
