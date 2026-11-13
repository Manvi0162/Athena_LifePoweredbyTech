"""Water module storage: one JSON file for now (single household account).

Kept behind load / save / reset / log so it can be swapped for Supabase tables
(households, water_assessments, water_bills, water_readings, water_actions,
water_forecasts, water_checks, water_activity) without touching the maths.
"""
import copy
import json
import os
import threading
from datetime import datetime, timezone

try:                                   # merged backend: one household per logged-in user (core/sync.py)
    from core import sync
except ImportError:                    # module copied on its own
    sync = None

HERE = os.path.dirname(__file__)
PATH = os.environ.get("WATER_STATE_FILE", os.path.join(HERE, "data", "water_state.json"))
EMPTY = os.path.join(HERE, "data", "empty_water.json")
SAMPLE = os.path.join(HERE, "data", "sample_water.json")
_lock = threading.Lock()


def load():
    if sync:
        state = sync.load_module_state("water", lambda: _read(EMPTY))
        if state is not None:
            return _overlay_shared(state)
    with _lock:
        if not os.path.exists(PATH):
            _write(_read(EMPTY))
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)


HOME_TYPES = {"House": "house", "Apartment": "apartment", "Shared home": "shared", "Other": "other"}


def _overlay_shared(state):
    """General answers live once, in the shared household; copy them in (onboarding G1-G4)."""
    shared = sync.shared_profile() or {}
    h = state.setdefault("household", {})
    if shared.get("members"):
        h["members"] = int(shared["members"])
    if shared.get("home_type"):
        h["home_type"] = HOME_TYPES.get(shared["home_type"], str(shared["home_type"]).lower())
    for k in ("occupancy", "main_goal"):
        if shared.get(k):
            h[k] = shared[k]
    p = state.setdefault("profile", {})
    if shared.get("region") and not p.get("region"):
        p["region"] = shared["region"]
    if shared.get("water_budget_rs") is not None:
        p["monthly_budget_rs"] = shared["water_budget_rs"]
    return state


def save(state):
    if sync and sync.save_module_state("water", state):
        return
    with _lock:
        _write(state)


def reset(sample=False):
    """Empty account (default) or the fictional sample household."""
    state = _read(SAMPLE if sample else EMPTY)
    if sync and sync.save_module_state("water", state):
        return copy.deepcopy(state)
    with _lock:
        _write(state)
        return copy.deepcopy(state)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write(state):
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, PATH)


def log(state, event, **details):
    state.setdefault("activity", []).append(
        {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "module": "water", "event": event, **details})
    state["activity"] = state["activity"][-300:]
    if sync:
        sync.log_activity("water", event, details)
