"""Water-saving actions: each saving is a visible formula with stated assumptions (no hidden model).

Litres saved per day -> m3 per day. The rupees saved are NOT m3 x an average price: the whole CWA tariff is
recalculated with and without the action (see advice.scenario), because rising blocks make the last m3 dearest.

Default values (the user can change every one of them):
  shower flow 7.9 L/min (2.1 gpm), 7.7 min per shower, toilet flush 9.8 L (2.6 gal), washing machine 111 L/load:
      Residential End Uses of Water, Version 2 (Water Research Foundation, 2016) averages
  dripping tap 31 L/day: US EPA WaterSense, "one drip per second wastes more than 3,000 gallons per year"
      (3,000 gal = 11,356 L / 365 days)
These are North-American measurements; Mauritian fixtures may differ, so the UI should let people enter their own.
"""
SHOWER_FLOW_L_MIN = 7.9
SHOWER_MINUTES = 7.7
FLUSH_L = 9.8
WASHER_L_PER_LOAD = 111
DRIP_L_DAY = 31

CATALOGUE = {
    "shorter_showers": {
        "title": "Shorter showers",
        "params": {"minutes_less": 2, "showers_per_day": None, "flow_l_per_min": SHOWER_FLOW_L_MIN},
        "limits": {"minutes_less": (0, 30), "showers_per_day": (0, 40), "flow_l_per_min": (2, 30)},
        "formula": "minutes_less x flow_l_per_min x showers_per_day",
        "assumptions": ["Shower flow 7.9 L/min (REU 2016 average) unless you measure yours",
                        "One shower per person per day unless changed"]},
    "toilet_greywater": {
        "title": "Flush with reused washing water",
        "params": {"flushes_per_day": None, "litres_per_flush": FLUSH_L},
        "limits": {"flushes_per_day": (0, 100), "litres_per_flush": (2, 20)},
        "formula": "flushes_per_day x litres_per_flush",
        "assumptions": ["Flush 9.8 L (REU 2016 average); dual-flush toilets use less",
                        "Two bucket-flushes per person per day unless changed"]},
    "fix_dripping_tap": {
        "title": "Fix a dripping tap",
        "params": {"taps": 1, "litres_per_day": DRIP_L_DAY},
        "limits": {"taps": (0, 20), "litres_per_day": (0, 500)},
        "formula": "taps x litres_per_day",
        "assumptions": ["One drip per second wastes about 31 L/day (US EPA WaterSense)"]},
    "full_laundry_loads": {
        "title": "Only run full laundry loads",
        "params": {"loads_less_per_week": 1, "litres_per_load": WASHER_L_PER_LOAD},
        "limits": {"loads_less_per_week": (0, 21), "litres_per_load": (10, 250)},
        "formula": "loads_less_per_week x litres_per_load / 7",
        "assumptions": ["111 L per washing-machine load (REU 2016 average); front-loaders use about half"]},
}


def resolved_params(key, params, profile):
    """Fill defaults from the household profile and check every value is in a sensible range."""
    if key not in CATALOGUE:
        raise KeyError(f"Unknown action '{key}'. Choose one of: {', '.join(CATALOGUE)}")
    spec = CATALOGUE[key]
    unknown = set(params or {}) - set(spec["params"])
    if unknown:
        raise ValueError(f"'{key}' does not take {', '.join(sorted(unknown))}. It takes: {', '.join(spec['params'])}")
    p = {**spec["params"], **{k: v for k, v in (params or {}).items() if v is not None}}
    people = max(1, int(profile.get("members", 1)))
    if key == "shorter_showers":
        p["showers_per_day"] = p["showers_per_day"] or profile.get("showers_per_day") or people
        p["flow_l_per_min"] = (params or {}).get("flow_l_per_min") or profile.get("shower_flow_l_per_min") or SHOWER_FLOW_L_MIN
    if key == "toilet_greywater" and not p["flushes_per_day"]:
        p["flushes_per_day"] = 2 * people
    for name, (lo, hi) in spec["limits"].items():
        try:
            v = float(p[name])
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a number")
        if not lo <= v <= hi:
            raise ValueError(f"{name} must be between {lo:g} and {hi:g} (got {v:g})")
        p[name] = v
    if key == "shorter_showers":
        usual = float(profile.get("shower_minutes") or SHOWER_MINUTES)
        if p["minutes_less"] > usual:
            raise ValueError(f"minutes_less ({p['minutes_less']:g}) is longer than the usual shower ({usual:g} min)")
    return p


def saving_per_day(key, params, profile):
    """m3 saved per day."""
    p = resolved_params(key, params, profile)
    if key == "shorter_showers":
        litres = p["minutes_less"] * p["flow_l_per_min"] * p["showers_per_day"]
    elif key == "toilet_greywater":
        litres = p["flushes_per_day"] * p["litres_per_flush"]
    elif key == "fix_dripping_tap":
        litres = p["taps"] * p["litres_per_day"]
    else:
        litres = p["loads_less_per_week"] * p["litres_per_load"] / 7
    return litres / 1000
