"""Electricity module storage: one JSON file for now (single household account).

Kept behind load / save / reset / log so it can be swapped for Supabase tables
(electricity_profile, electricity_bills, electricity_readings, electricity_actions, electricity_activity) without touching the maths.
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
PATH = os.environ.get("ELECTRICITY_STATE_FILE", os.path.join(HERE, "data", "electricity_state.json"))
DEMO = os.path.join(HERE, "data", "demo_electricity.json")
EMPTY = os.path.join(HERE, "data", "empty_electricity.json")
_lock = threading.Lock()


def _empty():
    with open(EMPTY, encoding="utf-8") as fh:
        return json.load(fh)


def _overlay_shared(state):
    """General answers live once, in the shared household (onboarding); copy them in."""
    shared = sync.shared_profile() or {}
    p = state.setdefault("profile", {})
    if shared.get("members"):
        p["members"] = int(shared["members"])
    if shared.get("electricity_budget_rs") is not None:
        p["monthly_budget_rs"] = shared["electricity_budget_rs"]
    return state


def load():
    if sync:                           # logged-in household: new accounts start empty, never with demo bills
        state = sync.load_module_state("electricity", _empty)
        if state is not None:
            return _overlay_shared(state)
    with _lock:
        if not os.path.exists(PATH):
            _write(_demo())
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)


def save(state):
    if sync and sync.save_module_state("electricity", state):
        return
    with _lock:
        _write(state)


def reset(sample=True):
    """Demo household (the team's real CEB bills) by default; sample=False gives an empty account."""
    state = _demo() if sample else _empty()
    if sync and sync.save_module_state("electricity", state):
        return copy.deepcopy(state)
    with _lock:
        _write(state)
        return copy.deepcopy(state)


def _demo():
    with open(DEMO, encoding="utf-8") as fh:
        return json.load(fh)


def _write(state):
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, PATH)


def log(state, event, **details):
    state.setdefault("activity", []).append(
        {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "module": "electricity", "event": event, **details})
    state["activity"] = state["activity"][-300:]
    if sync:
        sync.log_activity("electricity", event, details)
