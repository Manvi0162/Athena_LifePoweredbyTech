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

HERE = os.path.dirname(__file__)
PATH = os.environ.get("WATER_STATE_FILE", os.path.join(HERE, "data", "water_state.json"))
EMPTY = os.path.join(HERE, "data", "empty_water.json")
SAMPLE = os.path.join(HERE, "data", "sample_water.json")
_lock = threading.Lock()


def load():
    with _lock:
        if not os.path.exists(PATH):
            _write(_read(EMPTY))
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)


def save(state):
    with _lock:
        _write(state)


def reset(sample=False):
    """Empty account (default) or the fictional sample household."""
    with _lock:
        state = _read(SAMPLE if sample else EMPTY)
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
