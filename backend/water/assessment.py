"""Onboarding answers used by the water module.

General household questions (G1-G4): mandatory, shared by every module (stored by the team's backend, M2).
The water module keeps a copy so it can run alone. They are CONTEXT ONLY: they never replace bill m3.

Water questions (W1-W5): optional, skippable, editable. Every change creates a new VERSION.
Answers are ASSUMPTIONS, saved apart from measured m3. "not_sure" is kept as unknown, never filled in.
Band answers are turned into a single number (the middle of the band) only inside what-if scenarios,
and the scenario says so.
"""
from datetime import datetime, timezone

GENERAL = {
    "members": {"question": "How many people usually live in your household?", "type": "int", "min": 1, "max": 30},
    "home_type": {"question": "What type of home do you live in?",
                  "options": ["house", "apartment", "shared", "other"]},
    "occupancy": {"question": "When is your household usually occupied?",
                  "options": ["most_of_the_day", "evenings_and_nights", "variable"]},
    "main_goal": {"question": "What is your main household improvement goal?",
                  "options": ["reduce_expenses", "conserve_resources", "reduce_food_waste", "all"]},
}

QUESTIONS = {
    "W1_shower_minutes": {
        "question": "How long does each person typically spend showering or bathing daily?",
        "options": {"under_5": 4.0, "5_10": 7.5, "11_20": 15.5, "over_20": 25.0, "not_sure": None},
        "unit": "minutes per person per day (middle of the band)"},
    "W2_flushes_per_person": {
        "question": "Approximately how many times does each person flush the toilet per day?",
        "options": {"1_3": 2.0, "4_6": 5.0, "7_plus": 8.0, "not_sure": None},
        "unit": "flushes per person per day (middle of the band)"},
    "W3_laundry_loads_per_week": {
        "question": "How many loads of laundry does your household wash per week?",
        "options": {"1_2": 1.5, "3_5": 4.0, "6_plus": 7.0, "not_sure": None},
        "unit": "loads per week (middle of the band)"},
    "W4_outdoor_use": {
        "question": "How often do you use water for gardening, car washing or outdoor cleaning?",
        "options": {"never": 0.0, "weekly": 1.0, "several_per_week": 3.5, "daily": 7.0},
        "unit": "times per week"},
    "W5_expected_change": {
        "question": "Do you expect your household water usage to change next month?",
        "options": {"no": 0, "increase": 1, "decrease": -1, "not_sure": None},
        "extra": {"reason": "optional text", "change_pct": "optional number, e.g. 10 for about 10%"}},
}

# Team defaults for Mauritius (13 Nov 2026). Used only in scenarios and explanations, never added to the forecast:
# the bills already include normal life.
MAURITIUS_DEFAULTS = {
    "roof_tank": True, "bucket_baths": False, "car_wash_per_month": 1, "water_cuts": False,
    "note": "Different situations (cuts, guests, extra washing) are entered in the what-if section.",
}


def validate_general(data):
    out = {}
    for k, v in data.items():
        if k not in GENERAL:
            raise ValueError(f"Unknown general question '{k}'. Questions: {', '.join(GENERAL)}")
        spec = GENERAL[k]
        if spec.get("type") == "int":
            if not isinstance(v, int) or not spec["min"] <= v <= spec["max"]:
                raise ValueError(f"{k} must be a whole number between {spec['min']} and {spec['max']}")
        elif v not in spec["options"]:
            raise ValueError(f"{k} must be one of: {', '.join(spec['options'])}")
        out[k] = v
    return out


def validate_water(answers):
    out = {}
    for k, v in answers.items():
        if k in ("W5_reason", "W5_change_pct"):
            continue
        if k not in QUESTIONS:
            raise ValueError(f"Unknown water question '{k}'. Questions: {', '.join(QUESTIONS)}")
        if v not in QUESTIONS[k]["options"]:
            raise ValueError(f"{k} must be one of: {', '.join(QUESTIONS[k]['options'])}")
        out[k] = v
    if "W5_reason" in answers:
        out["W5_reason"] = str(answers["W5_reason"])[:300]
    if answers.get("W5_change_pct") is not None:
        pct = float(answers["W5_change_pct"])
        if not 0 <= pct <= 100:
            raise ValueError("W5_change_pct is the size of the change in %, between 0 and 100")
        out["W5_change_pct"] = pct
    return out


def latest(state):
    versions = state.get("assessments", [])
    return versions[-1] if versions else {"version": 0, "answers": {}}


def save_version(state, answers):
    """Merge new answers into the latest version and store them as a new version."""
    merged = {**latest(state)["answers"], **validate_water(answers)}
    v = {"version": latest(state)["version"] + 1,
         "answered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "answers": merged}
    state.setdefault("assessments", []).append(v)
    return v


def value(state, key):
    """Numeric value of an answer, or None if unanswered or 'not sure'."""
    a = latest(state)["answers"].get(key)
    return None if a is None else QUESTIONS[key]["options"].get(a)


def known(state, key):
    return value(state, key) is not None


def complete(state):
    return all(known(state, k) for k in QUESTIONS)
