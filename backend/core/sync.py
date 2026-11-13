"""How the modules share one household database without calling each other.

Water and electricity keep their detailed state (assessments, forecast snapshots, goals) as one JSON
document per household and module in the `module_state` table (sql/03_module_state.sql). They also write
the shared facts into the team's common tables, so food, Big Brain and Supabase dashboards see them:
  utility_bills, meter_readings  <- confirmed bills and meter readings
  household_actions              <- goals selected / completed
  activity_logs                  <- every event (bill added, assessment answered, scenario run...)
Every write here is best effort: if the shared table is unavailable the module still works, and the
problem is logged instead of breaking the user's action.
When no one is logged in (module tests, standalone module apps) these functions do nothing.
"""
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def current():
    """(RequestContext, household) for the caller, or (None, None)."""
    try:
        from .identity import CURRENT, household
    except Exception:                                  # module used outside the merged backend
        return None, None
    ctx = CURRENT.get()
    if ctx is None:
        return None, None
    return ctx, household(ctx)


def load_module_state(module, template):
    ctx, h = current()
    if not h:
        return None
    rows = (ctx.db.table("module_state").select("state").eq("household_id", h["id"]).eq("module", module)
            .limit(1).execute().data or [])
    return rows[0]["state"] if rows else template()


def save_module_state(module, state):
    ctx, h = current()
    if not h:
        return False
    ctx.db.table("module_state").upsert({"household_id": h["id"], "module": module, "state": state,
                                         "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                        on_conflict="household_id,module").execute()
    return True


def _safe(fn):
    def wrapper(*a, **k):
        ctx, h = current()
        if not h:
            return None
        try:
            return fn(ctx, h, *a, **k)
        except Exception as exc:
            log.warning("Shared-table write skipped (%s): %s", fn.__name__, exc)
            return None
    return wrapper


@_safe
def log_activity(ctx, h, module, event, details=None):
    ctx.db.table("activity_logs").insert({"household_id": h["id"], "event_type": f"{module}.{event}",
                                          "details": {"module": module, **(details or {})}}).execute()


@_safe
def mirror_bill(ctx, h, kind, start, end, units, amount, tariff_code, module_id):
    rows = ctx.db.table("utility_bills").insert({
        "household_id": h["id"], "kind": kind, "period_start": start, "period_end": end, "units": units,
        "amount": round(float(amount), 2), "tariff_code": f"{tariff_code} [{kind} module id {module_id}]"}).execute().data
    return rows[0]["id"] if rows else None


@_safe
def remove_bill(ctx, h, db_id):
    if db_id:
        ctx.db.table("utility_bills").delete().eq("id", db_id).eq("household_id", h["id"]).execute()


@_safe
def mirror_reading(ctx, h, kind, value, day):
    rows = ctx.db.table("meter_readings").insert({"household_id": h["id"], "kind": kind, "reading": value,
                                                  "captured_at": f"{day}T12:00:00+04:00"}).execute().data
    return rows[0]["id"] if rows else None


@_safe
def remove_reading(ctx, h, db_id):
    if db_id:
        ctx.db.table("meter_readings").delete().eq("id", db_id).eq("household_id", h["id"]).execute()


@_safe
def mirror_action(ctx, h, module, key, params, status, db_id=None):
    if db_id:
        ctx.db.table("household_actions").update({"status": status}).eq("id", db_id).execute()
        return db_id
    rows = ctx.db.table("household_actions").insert({"household_id": h["id"], "action_type": f"{module}:{key}",
                                                     "assumptions": params or {}, "status": status}).execute().data
    return rows[0]["id"] if rows else None


def shared_profile():
    """The household's general answers (onboarding), or None when nobody is logged in.
    Water and electricity overlay these on their own copy, so changing the household size once updates all."""
    ctx, h = current()
    if not h:
        return None
    prefs = h.get("preferences") or {}
    goals = h.get("budget_goals") or {}
    return {"members": h.get("members"), "home_type": prefs.get("home_type"), "occupancy": prefs.get("occupancy"),
            "main_goal": prefs.get("main_goal"), "region": prefs.get("region"),
            "monthly_target_rs": goals.get("monthly_target"),
            "water_budget_rs": goals.get("water_budget"), "electricity_budget_rs": goals.get("electricity_budget")}
