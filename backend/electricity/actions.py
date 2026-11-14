
"""Electricity-saving actions with assessment-based eligibility and transparent estimates."""

APPLIANCES_KW = {
    "air_conditioner": 1.2,
    "water_heater": 3.0,
    "iron": 1.0,
    "washing_machine": 0.5,
    "television": 0.1,
    "desktop_computer": 0.15,
    "kettle": 2.0,
    "fan": 0.06
}

CATALOGUE = {
    "appliance_hours": {
        "title": "Use an appliance less",
        "params": {
            "appliance": "air_conditioner",
            "kw": None,
            "hours_less_per_day": 1
        },
        "limits": {
            "kw": (0.001, 10),
            "hours_less_per_day": (0, 24)
        },
        "formula": "appliance power (kW) x hours saved per day",
        "assumptions": [
            "Typical appliance power is estimated unless you enter the value on its label."
        ]
    },
    "cooking_hours": {
        "title": "Reduce electric cooking time",
        "params": {
            "kw": None,
            "hours_less_per_day": 1
        },
        "limits": {
            "kw": (0.001, 10),
            "hours_less_per_day": (0, 24)
        },
        "formula": "cooking appliance power (kW) x hours saved per day",
        "assumptions": [
            "Enter the cooking appliance's rated power; no default power is assumed."
        ]
    },
    "standby_off": {
        "title": "Switch off standby at the plug",
        "params": {
            "standby_watts": 20,
            "hours_per_day": 20
        },
        "limits": {
            "standby_watts": (0, 500),
            "hours_per_day": (0, 24)
        },
        "formula": "standby power (W) / 1000 x hours per day",
        "assumptions": [
            "About 20 W of devices on standby; estimated unless you enter a measured value."
        ]
    }
}


def _assessment(state):
    """Read assessment answers without assuming missing answers."""
    return state.get("assessment", {}) or {}


def _answer(assessment, primary, fallback):
    """Support both descriptive keys and E1–E5 keys."""
    value = assessment.get(primary)

    if value is None:
        value = assessment.get(fallback)

    return value


def _selected_appliances(state):
    assessment = _assessment(state)
    selected = _answer(assessment, "appliances", "E1") or []

    if isinstance(selected, str):
        selected = [selected]

    if not isinstance(selected, (list, tuple, set)):
        return set()

    return {
        str(item).strip().lower().replace(" ", "_")
        for item in selected
    }


def eligibility(key, params, state):
    """Check whether an action is relevant to the assessment answers."""
    assessment = _assessment(state)
    params = params or {}

    if key == "standby_off":
        return True, None

    if key == "cooking_hours":
        cooking = _answer(assessment, "cooking_energy", "E4")

        cooked = str(cooking).strip().lower()
        if cooking is None or cooked in ("", "not_sure", "not sure", "unsure"):
            return False, "Answer Electricity question 4 to check whether electric cooking applies."

        if str(cooking).strip().lower() not in ("electric", "both"):
            return False, "This action applies only if you use electric cooking."

        if params.get("kw") is None:
            return False, "Enter the rated power (kW) of your electric cooking appliance."

        return True, None

    if key != "appliance_hours":
        return False, "Unknown action."

    appliance = str(params.get("appliance", "air_conditioner")).strip().lower()
    selected = _selected_appliances(state)

    if appliance not in selected:
        return False, (
            f"This action is unavailable because {appliance.replace('_', ' ')} "
            "was not selected in Electricity question 1."
        )

    if appliance == "air_conditioner":
        hours = _answer(assessment, "ac_hours", "E2")

        normalized = str(hours).strip().lower()
        if hours is None or normalized in ("", "not_sure", "not sure", "unsure"):
            return False, (
                "Tell us how many hours a day you use the air conditioner "
                "(Electricity question 2)."
            )

        if str(hours).strip().lower() == "none":
            return False, "Your assessment indicates that you do not use air conditioning."

    if appliance == "water_heater":
        heating = _answer(assessment, "water_heating", "E3")

        normalized = str(heating).strip().lower()
        if heating is None or normalized in ("", "not_sure", "not sure", "unsure"):
            return False, "Answer Electricity question 3 to check your water-heating type."

        if str(heating).strip().lower() != "electric":
            return False, "This action applies only when your water heating is electric."

    return True, None


def resolved_params(key, params=None, profile=None):
    """Apply defaults and validate all action parameters."""
    if key not in CATALOGUE:
        raise KeyError(
            f"Unknown action '{key}'. Choose one of: {', '.join(CATALOGUE)}"
        )

    spec = CATALOGUE[key]
    params = params or {}

    unknown = set(params) - set(spec["params"])

    if unknown:
        raise ValueError(
            f"'{key}' does not take {', '.join(sorted(unknown))}. "
            f"It takes: {', '.join(spec['params'])}"
        )

    p = {
        **spec["params"],
        **{k: v for k, v in params.items() if v is not None}
    }

    if key == "appliance_hours":
        appliance = p["appliance"]

        if appliance not in APPLIANCES_KW and p.get("kw") is None:
            raise ValueError(
                f"Unknown appliance '{appliance}'. Enter its power in kW "
                f"or choose: {', '.join(APPLIANCES_KW)}"
            )

        if p["kw"] is None:
            p["kw"] = APPLIANCES_KW.get(appliance)

        if p["kw"] is None:
            raise ValueError("Enter the appliance power in kW.")

    if key == "cooking_hours" and p["kw"] is None:
        raise ValueError("Enter the cooking appliance power in kW.")

    for name, (lo, hi) in spec["limits"].items():
        try:
            value = float(p[name])
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a number.")

        if not lo <= value <= hi:
            raise ValueError(
                f"{name} must be between {lo:g} and {hi:g} "
                f"(got {value:g})."
            )

        p[name] = value

    return p


def power_is_estimated(key, params=None):
    """Check whether the action uses an estimated default power."""
    params = params or {}

    if key == "appliance_hours":
        return params.get("kw") is None

    if key == "standby_off":
        return params.get("standby_watts") is None

    return False


def saving_per_day(key, params, profile=None):
    """Calculate estimated kWh saved per day."""
    p = resolved_params(key, params, profile)

    if key in ("appliance_hours", "cooking_hours"):
        return p["kw"] * p["hours_less_per_day"]

    if key == "standby_off":
        return p["standby_watts"] / 1000 * p["hours_per_day"]

    raise KeyError(f"Unknown action '{key}'.")
