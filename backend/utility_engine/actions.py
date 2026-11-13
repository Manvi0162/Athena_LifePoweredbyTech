"""What-if actions: every saving is a formula with stated assumptions (no hidden model).

Water:       litres/day saved -> m3/day
Electricity: kWh/day saved = appliance power (kW) x hours less per day   (blueprint formula)
The money saved is NOT units x average price: the full tariff is recalculated with and without the action.
"""
SHOWER_FLOW_L_MIN = 7.6     # median shower flow, REU 2016 residential end-use study (USA)
FLUSH_L = 8.8               # median toilet flush, REU 2016
APPLIANCES_KW = {           # typical power ratings; the user can change the value
    "air_conditioner": 1.2, "water_heater": 3.0, "iron": 1.0, "washing_machine": 0.5,
    "television": 0.1, "desktop_computer": 0.15, "kettle": 2.0, "fan": 0.06}

CATALOGUE = {
    "shorter_showers": {"utility": "water", "title": "Shorter showers",
                        "params": {"minutes_less": 2, "showers_per_day": None},
                        "formula": "minutes_less x 7.6 L/min x showers_per_day",
                        "assumptions": ["Shower flow 7.6 L/min (REU 2016 median)", "One shower per person per day unless changed"]},
    "toilet_greywater": {"utility": "water", "title": "Flush with reused washing water",
                         "params": {"flushes_per_day": None},
                         "formula": "flushes_per_day x 8.8 L",
                         "assumptions": ["Flush 8.8 L (REU 2016 median)", "Two flushes per person per day unless changed"]},
    "fix_dripping_tap": {"utility": "water", "title": "Fix a dripping tap",
                         "params": {"litres_per_day": 20},
                         "formula": "litres_per_day",
                         "assumptions": ["A steady drip wastes about 20 L/day (change to your measured value)"]},
    "full_laundry_loads": {"utility": "water", "title": "Only run full laundry loads",
                           "params": {"loads_less_per_week": 1, "litres_per_load": 60},
                           "formula": "loads_less_per_week x litres_per_load / 7",
                           "assumptions": ["About 60 L per washing-machine load (change for your machine)"]},
    "appliance_hours": {"utility": "electricity", "title": "Use an appliance less",
                        "params": {"appliance": "air_conditioner", "kw": None, "hours_less_per_day": 1},
                        "formula": "kW x hours_less_per_day",
                        "assumptions": ["Typical appliance power unless you enter your own"]},
    "standby_off": {"utility": "electricity", "title": "Switch off standby at the plug",
                    "params": {"standby_watts": 20, "hours_per_day": 20},
                    "formula": "standby_watts / 1000 x hours_per_day",
                    "assumptions": ["About 20 W of devices on standby (TV box, chargers, microwave)"]},
}


def resolved_params(key, params, household):
    p = {**CATALOGUE[key]["params"], **(params or {})}
    people = max(1, int(household.get("members", 1)))
    if key == "shorter_showers" and not p.get("showers_per_day"):
        p["showers_per_day"] = people
    if key == "toilet_greywater" and not p.get("flushes_per_day"):
        p["flushes_per_day"] = 2 * people
    if key == "appliance_hours" and not p.get("kw"):
        p["kw"] = APPLIANCES_KW.get(p.get("appliance"), 1.0)
    return p


def saving_per_day(key, params, household):
    """Units saved per day: m3 for water, kWh for electricity."""
    p = resolved_params(key, params, household)
    if key == "shorter_showers":
        return p["minutes_less"] * SHOWER_FLOW_L_MIN * p["showers_per_day"] / 1000
    if key == "toilet_greywater":
        return p["flushes_per_day"] * FLUSH_L / 1000
    if key == "fix_dripping_tap":
        return p["litres_per_day"] / 1000
    if key == "full_laundry_loads":
        return p["loads_less_per_week"] * p["litres_per_load"] / 7 / 1000
    if key == "appliance_hours":
        return p["kw"] * p["hours_less_per_day"]
    if key == "standby_off":
        return p["standby_watts"] / 1000 * p["hours_per_day"]
    raise KeyError(key)
