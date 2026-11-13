from datetime import date

from utility_engine import actions, advice
from utility_engine.forecast import forecast
from utility_engine.history import daily_history


def test_synthetic_days_add_up_to_each_real_bill(household):
    hist = daily_history(household, "electricity")
    for b in [x for x in household["bills"] if x["utility"] == "electricity"]:
        s = sum(d["units"] for d in hist if b["start"] <= d["date"] < b["end"])
        assert abs(s - b["units"]) < 0.05
    assert {d["kind"] for d in hist} == {"bill", "synthetic"}


def test_history_is_repeatable(household):
    assert daily_history(household, "water") == daily_history(household, "water")


def test_forecast_has_range_cost_and_evidence(household):
    f = forecast(household, "electricity")
    assert f["units"]["low"] <= f["units"]["mid"] <= f["units"]["high"]
    assert f["cost_rs"]["low"] <= f["cost_rs"]["mid"] <= f["cost_rs"]["high"]
    for k in ("period_start", "period_end", "method", "assumptions", "source_data", "currency"):
        assert k in f
    assert f["confidence"] == "good"


def test_scenario_recomputes_full_tariff(household):
    s = advice.scenario(household, "appliance_hours", {"appliance": "air_conditioner", "hours_less_per_day": 1})
    assert s["saving_units_per_day"] == 1.2                       # 1.2 kW x 1 h
    assert s["difference"]["cost_rs"] < 0 and s["per_full_month"]["units"] == 36.0


def test_completed_action_lowers_following_days(household):
    before = forecast(household, "water")["units"]["mid"]
    household["actions"] = [{"id": "a1", "key": "shorter_showers", "utility": "water", "params": {"minutes_less": 2},
                             "status": "completed", "completed_on": "2026-11-01"}]
    after = forecast(household, "water")["units"]["mid"]
    per_day = actions.saving_per_day("shorter_showers", {"minutes_less": 2}, household)   # 2 x 7.6 x 4 = 60.8 L
    assert abs(per_day - 0.0608) < 1e-9 and after < before


def test_insights_rank_actions_and_benchmark(household):
    i = advice.insights(household)
    assert any(r["kind"] == "action" for r in i["recommendations"])
    assert {b["utility"] for b in i["benchmarks"]} == {"water", "electricity"}
    assert i["total_projected_rs"] > 0
