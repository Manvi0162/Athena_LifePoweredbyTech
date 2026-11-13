"""Household storage: one JSON file for now (single account).

Kept behind three functions so it can be replaced by Supabase tables (households, utility_bills,
meter_readings, household_actions, activity_logs) without touching the engine.
"""
import copy
import json
import os
import threading
from datetime import datetime, timezone

PATH = os.environ.get("HOUSEHOLD_FILE", os.path.join(os.path.dirname(__file__), "..", "data", "household.json"))
DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "demo_household.json")
_lock = threading.Lock()


def load():
    with _lock:
        if not os.path.exists(PATH):
            reset()
        with open(PATH) as fh:
            return json.load(fh)


def save(h):
    with _lock:
        tmp = PATH + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(h, fh, indent=1)
        os.replace(tmp, PATH)


def reset():
    with open(DEMO) as fh:
        h = json.load(fh)
    with open(PATH, "w") as fh:
        json.dump(h, fh, indent=1)
    return copy.deepcopy(h)


def log(h, event, **details):
    h.setdefault("activity", []).append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                         "event": event, **details})
    h["activity"] = h["activity"][-300:]
