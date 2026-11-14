"""What-if: formulas, needs_input, and never touching real history."""
import copy

import pytest

from water import assessment as A
from water import forecast as F
from water import scenarios as SC

from .conftest import ALL_ANSWERS


def test_scenario_without_answers_says_not_enough_data(one_bill):
    r = SC.run(one_bill, "shorter_showers", {})
    assert r["status"] == "needs_input" and "W1" in r["message"]


def test_not_sure_is_not_enough(one_bill):
    A.save_version(one_bill, {"W1_shower_minutes": "not_sure"})
    assert SC.run(one_bill, "shorter_showers", {})["status"] == "needs_input"


def test_shower_formula_and_full_tariff(one_bill):
    A.save_version(one_bill, ALL_ANSWERS)
    r = SC.run(one_bill, "shorter_showers", {"minutes_less": 2, "flow_l_per_min": 8})
    assert r["status"] == "ok" and r["change_litres_per_day"] == -64.0            # 4 x 2 x 8 (spec example)
    assert r["difference"]["litres"] == -1920                                      # x 30 days
    assert r["difference"]["rs"] < 0 and "whole CWA tariff" in r["cost_how"]


def test_without_bill_gives_litres_only(empty):
    empty["household"]["members"] = 4
    A.save_version(empty, ALL_ANSWERS)
    r = SC.run(empty, "shorter_showers", {})
    assert r["status"] == "partial" and "rupee" in r["message"] and r["difference"]["litres"] < 0


def test_required_value_is_asked_not_guessed(one_bill):
    A.save_version(one_bill, ALL_ANSWERS)
    r = SC.run(one_bill, "less_outdoor_water", {})
    assert r["status"] == "needs_input" and "10 L bucket" in r["message"]
    assert SC.run(one_bill, "less_outdoor_water", {"litres_per_session": 80})["status"] == "ok"


def test_never_outdoors_means_nothing_to_reduce(one_bill):
    A.save_version(one_bill, {**ALL_ANSWERS, "W4_outdoor_use": "never"})
    r = SC.run(one_bill, "less_outdoor_water", {"litres_per_session": 80})
    assert r["status"] == "needs_input" and "never" in r["message"]


def test_impossible_values_are_refused(one_bill):
    A.save_version(one_bill, ALL_ANSWERS)
    with pytest.raises(ValueError, match="shorter than your usual"):
        SC.run(one_bill, "shorter_showers", {"minutes_less": 9})
    with pytest.raises(ValueError, match="loads a week"):
        SC.run(one_bill, "full_laundry_loads", {"loads_less_per_week": 6})
    with pytest.raises(ValueError, match="does not take"):
        SC.run(one_bill, "fix_dripping_tap", {"kw": 1})


def test_guests_use_measured_per_person_rate(one_bill):
    r = SC.run(one_bill, "guests_or_away", {"people_change": 2, "days": 7})
    assert r["difference"]["litres"] == 2100                                       # 600/4 x 2 x 7


def test_scenario_does_not_change_history(one_bill):
    A.save_version(one_bill, ALL_ANSWERS)
    before = copy.deepcopy(one_bill)
    SC.run(one_bill, "shorter_showers", {})
    assert one_bill == before
    assert F.forecast(one_bill)["estimated_units"] == F.forecast(before)["estimated_units"]


def test_completed_goal_lowers_forecast(one_bill):
    A.save_version(one_bill, ALL_ANSWERS)
    before = F.forecast(one_bill)["estimated_units"]
    one_bill["actions"] = [{"id": "a1", "key": "fix_dripping_tap", "params": {}, "status": "completed", "completed_on": "2026-10-20"}]
    f = F.forecast(one_bill)
    assert f["estimated_units"] < before and any(l["kind"] == "action" for l in f["lines"])
