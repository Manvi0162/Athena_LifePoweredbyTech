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
    state = rows[0]["state"] if rows else template()
    try:
        import_shared_rows(ctx, h, module, state)
    except Exception as exc:                       # never block the module because of the shared tables
        log.warning("Import from shared tables skipped (%s): %s", module, exc)
    return state


def import_shared_rows(ctx, h, module, state):
    """Bills and meter readings that exist in the team database but not in the module's state (e.g. the
    database owner's seed data, or rows added by another tool) are added to the module, so the module
    calculates with every confirmed bill. Rows the module wrote itself carry their db_id and are skipped."""
    unit = "m3" if module == "water" else "kwh"
    known = {b.get("db_id") for b in state.get("bills", [])} | {r.get("db_id") for r in state.get("readings", [])}
    bills = (ctx.db.table("utility_bills").select("*").eq("household_id", h["id"]).eq("kind", module)
             .execute().data or [])
    state["bills"] = [b for b in state.get("bills", []) if b.get("source") != "placeholder" or not bills]
    for r in sorted(bills, key=lambda r: str(r.get("period_start"))):
        if r["id"] in known or r.get("units") is None:
            continue
        start, end = str(r["period_start"])[:10], str(r["period_end"])[:10]
        if any(start < b["end"] and b["start"] < end for b in state["bills"]):
            continue                                # overlaps a bill the module already has
        bill = {"id": "db" + str(r["id"]).replace("-", "")[:8], "start": start, "end": end, unit: float(r["units"]),
                "amount_rs": float(r["amount"]) if r.get("amount") is not None else None,
                "end_reading": r.get("end_meter_reading"), "source": "database", "db_id": r["id"]}
        if module == "water":
            bill.update(start_reading=r.get("start_meter_reading"), ocr_id=None)
        else:
            code = str(r.get("tariff_code") or "")
            bill["tariff_class"] = next((c for c in ("110", "120", "140") if c in code), None)
        state["bills"].append(bill)
    state["bills"].sort(key=lambda b: b["start"])
    last_end = max((b["end"] for b in state["bills"]), default="")
    key = "index_m3" if module == "water" else "index_kwh"
    readings = (ctx.db.table("meter_readings").select("*").eq("household_id", h["id"]).eq("kind", module)
                .execute().data or [])
    days = {x["date"] for x in state.get("readings", [])}
    for r in readings:
        day = str(r.get("captured_at"))[:10]
        if r["id"] in known or day <= last_end or day in days or r.get("reading") is None:
            continue
        state.setdefault("readings", []).append({"id": "db" + str(r["id"]).replace("-", "")[:8], "date": day,
                                                 key: float(r["reading"]), "db_id": r["id"]})
        days.add(day)
    return state


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
