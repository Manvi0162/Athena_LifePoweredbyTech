from electricity import actions, advice
from electricity.forecast import forecast
from electricity.history import daily_history
from electricity.tariff import electricity_bill
from copy import deepcopy


def test_real_ceb_bill_145_kwh():
    b = electricity_bill(145, tariff_code="140", tv_licence=True)
    assert round(b.lines[0][1]) == 828 and round(b.total) == 998


def test_minimum_charge():
    assert electricity_bill(5, tariff_code="140").lines[0][1] == 424.35


def test_days_add_up_to_each_bill(state):
    hist = daily_history(state)
    for b in state["bills"]:
        assert abs(sum(d["kwh"] for d in hist if b["start"] <= d["date"] < b["end"]) - b["kwh"]) < 0.05


def test_forecast_and_scenario(state):
    f = forecast(state)
    assert f["status"] == "ok"
    assert f["forecast_status"] == "preliminary"
    assert f["confidence"] == "medium"
    # Missing assessment: scenario must request more information.
    s = advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "air_conditioner", "hours_less_per_day": 1}
    )
    assert s["status"] == "needs_input"
    assert "question 1" in s["message"].lower()

    # Assessment completed: scenario can be calculated.
    state["assessment"] = {
        "appliances": ["air_conditioner"],
        "ac_hours": "4-8"
    }

    s = advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "air_conditioner", "hours_less_per_day": 1}
    )

    assert s["status"] == "ok"
    assert s["saving_kwh_per_day"] == 1.2
    assert s["per_full_month"]["kwh"] == -36.0
    assert s["difference"]["cost_rs"] < 0

def test_summary_contract(state):
    s = advice.summary(state)
    assert s["module"] == "electricity" and s["forecast"]["unit"] == "kWh" and s["recommendations"]


def test_api(client):
    assert client.get("/electricity/summary").status_code == 200
    r = client.post("/electricity/scenarios", json={"action": "appliance_hours", "params": {"hours_less_per_day": 30}})
    assert r.status_code == 422
    assert client.put("/electricity/profile", json={"ceb_tariff": "999"}).status_code == 422


def test_water_heater_scenario(state):
    state["assessment"] = {
        "appliances": ["water_heater"],
        "water_heating": "electric"
    }

    result = advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "water_heater", "hours_less_per_day": 1}
    )

    assert result["status"] == "ok"
    assert result["saving_kwh_per_day"] == 3.0


def test_water_heater_not_electric(state):
    state["assessment"] = {
        "appliances": ["water_heater"],
        "water_heating": "solar"
    }

    result = advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "water_heater", "hours_less_per_day": 1}
    )

    assert result["status"] == "needs_input"


def test_washing_machine_scenario(state):
    state["assessment"] = {
        "appliances": ["washing_machine"]
    }

    result = advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "washing_machine", "hours_less_per_day": 1}
    )

    assert result["status"] == "ok"
    assert result["saving_kwh_per_day"] == 0.5


def test_cooking_scenario(state):
    state["assessment"] = {
        "cooking_energy": "both"
    }

    result = advice.scenario(
        state,
        "cooking_hours",
        {"kw": 2.0, "hours_less_per_day": 1}
    )

    assert result["status"] == "ok"
    assert result["saving_kwh_per_day"] == 2.0


def test_cooking_not_electric(state):
    state["assessment"] = {
        "cooking_energy": "gas"
    }

    result = advice.scenario(
        state,
        "cooking_hours",
        {"kw": 2.0, "hours_less_per_day": 1}
    )

    assert result["status"] == "needs_input"


def test_standby_scenario(state):
    result = advice.scenario(state, "standby_off")

    assert result["status"] == "ok"
    assert result["saving_kwh_per_day"] == 0.4


def test_scenario_does_not_modify_household_data(state):
    original = deepcopy(state)

    state["assessment"] = {
        "appliances": ["air_conditioner"],
        "ac_hours": "4-8"
    }

    original["assessment"] = deepcopy(state["assessment"])

    advice.scenario(
        state,
        "appliance_hours",
        {"appliance": "air_conditioner", "hours_less_per_day": 1}
    )

    assert state["bills"] == original["bills"]
    assert state["readings"] == original["readings"]
    assert state["activity"] == original["activity"]


def test_e5_increase(state):
    state["assessment"] = {
        "expected_use": "increase",
        "expected_change_kwh": 20
    }

    result = forecast(state)

    assert result["adjustments"]["expected_use_change"]["status"] == "applied"
    assert result["adjustments"]["expected_use_change"]["delta_kwh"] == 20


def test_e5_decrease_percentage(state):
    state["assessment"] = {
        "expected_use": "decrease",
        "expected_change_pct": 10
    }

    result = forecast(state)

    adjustment = result["adjustments"]["expected_use_change"]

    assert adjustment["status"] == "applied"
    assert adjustment["delta_kwh"] < 0


def test_e5_missing_amount(state):
    state["assessment"] = {
        "expected_use": "increase"
    }

    result = forecast(state)

    assert result["adjustments"]["expected_use_change"]["status"] == "needs_input"
    assert result["adjustments"]["expected_use_change"]["delta_kwh"] == 0


def test_e5_no_change(state):
    state["assessment"] = {
        "expected_use": "no"
    }

    result = forecast(state)

    assert result["adjustments"]["expected_use_change"]["status"] == "no_change"
    assert result["adjustments"]["expected_use_change"]["delta_kwh"] == 0


def test_e5_does_not_modify_bills(state):
    from copy import deepcopy

    original_bills = deepcopy(state["bills"])

    state["assessment"] = {
        "expected_use": "increase",
        "expected_change_kwh": 15
    }

    forecast(state)

    assert state["bills"] == original_bills

