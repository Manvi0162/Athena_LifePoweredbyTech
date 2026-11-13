from water import actions, advice
from water.forecast import forecast
from water.history import daily_history


def test_days_add_up_to_each_bill(state):
    hist = daily_history(state)
    for b in state["bills"]:
        assert abs(sum(d["m3"] for d in hist if b["start"] <= d["date"] < b["end"]) - b["m3"]) < 0.01
    assert {d["kind"] for d in hist} == {"bill", "synthetic"}


def test_history_is_repeatable(state):
    assert daily_history(state) == daily_history(state)


def test_meter_readings_are_real_days(state):
    state["readings"] = [{"id": "r1", "date": "2026-11-03", "index_m3": 1460.0}]   # 8 m3 in 21 days
    hist = daily_history(state)
    reading_days = [d for d in hist if d["kind"] == "reading"]
    assert len(reading_days) == 21 and abs(sum(d["m3"] for d in reading_days) - 8.0) < 0.01
    f = forecast(state)
    assert "meter readings" in f["method"]


def test_forecast_has_range_cost_evidence(state):
    f = forecast(state)
    assert f["m3"]["low"] <= f["m3"]["mid"] <= f["m3"]["high"]
    assert f["cost_rs"]["low"] <= f["cost_rs"]["mid"] <= f["cost_rs"]["high"]
    for k in ("period_start", "period_end", "method", "assumptions", "source_data", "currency", "confidence"):
        assert k in f
    assert f["confidence"] == "low"                     # placeholders only


def test_shower_formula():
    # 2 min x 7.9 L/min x 4 showers = 63.2 L/day
    assert abs(actions.saving_per_day("shorter_showers", {"minutes_less": 2}, {"members": 4}) - 0.0632) < 1e-9


def test_invalid_params_are_refused():
    import pytest
    with pytest.raises(ValueError, match="between"):
        actions.resolved_params("shorter_showers", {"minutes_less": 99}, {"members": 4})
    with pytest.raises(ValueError, match="does not take"):
        actions.resolved_params("fix_dripping_tap", {"kw": 1}, {"members": 4})


def test_scenario_recomputes_tariff(state):
    s = advice.scenario(state, "shorter_showers", {"minutes_less": 2})
    assert s["difference"]["m3"] < 0 and s["difference"]["cost_rs"] < 0
    assert s["per_full_month"]["litres"] == -1896                # 63.2 L x 30


def test_completed_action_lowers_forecast(state):
    before = forecast(state)["m3"]["mid"]
    state["actions"] = [{"id": "a1", "key": "shorter_showers", "params": {"minutes_less": 2},
                         "status": "completed", "completed_on": "2026-11-01"}]
    assert forecast(state)["m3"]["mid"] < before


def test_unusual_usage_alert(state):
    state["bills"][-1]["m3"] = 40                         # big jump in the latest bill
    ids = [r["id"] for r in advice.insights(state)["recommendations"]]
    assert "check_for_leaks" in ids


def test_summary_follows_contract(state):
    s = advice.summary(state)
    for k in ("module", "status", "currency", "period_start", "period_end", "forecast", "recommendations", "recent_activity"):
        assert k in s
    assert s["module"] == "water" and s["forecast"]["unit"] == "m3"
    assert all({"id", "kind", "title", "evidence"} <= set(r) for r in s["recommendations"])
