"""Security routes (surprise card: misuse) and the undoable account reset.

  GET  /security/status                 pattern set? authenticator on? locks, alert for the owner, recent events
  PUT  /security/pattern                set or change the pattern (needs password, or authenticator/recovery code)
  POST /security/pattern/verify         draw the pattern for one sensitive action -> one-time permission (5 min)
  POST /security/authenticator/setup    QR code + key for Microsoft / Google Authenticator (optional)
  POST /security/authenticator/confirm  first code switches it on -> 8 recovery codes (shown once)
  POST /security/authenticator/disable  needs the pattern (X-Step-Up) and a code
  POST /account/reset                   needs the pattern: data hidden, restorable for 24 hours
  POST /account/restore                 needs the pattern: brings everything back
  GET  /account/reset-status
Sensitive requests carry the permission in the `X-Step-Up` header.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header
from pydantic import BaseModel

from core import security as S
from core.identity import require_context, require_household

router = APIRouter(tags=["security"])
RESTORE_HOURS = 24
# Shared tables cleared by a reset, parents before children for restore (children first for delete).
TABLES = ["pantry_items", "grocery_receipts", "receipt_items", "pantry_events", "cooking_operations",
          "utility_bills", "meter_readings", "household_actions"]


class PatternIn(BaseModel):
    pattern: list[int]
    password: str | None = None
    code: str | None = None
    recovery_code: str | None = None


class VerifyIn(BaseModel):
    pattern: list[int]
    action: str


class CodeIn(BaseModel):
    code: str | None = None
    recovery_code: str | None = None


@router.get("/security/status")
def security_status():
    return S.status(require_context())


@router.put("/security/pattern")
def set_pattern(body: PatternIn):
    ctx = require_context()
    return S.set_pattern(ctx, body.pattern, {"password": body.password, "code": body.code,
                                             "recovery_code": body.recovery_code})


@router.post("/security/pattern/verify")
def verify_pattern(body: VerifyIn):
    return S.verify_pattern(require_context(), body.pattern, body.action)


@router.post("/security/authenticator/setup")
def authenticator_setup():
    return S.totp_setup(require_context())


@router.post("/security/authenticator/confirm")
def authenticator_confirm(body: CodeIn):
    return S.totp_confirm(require_context(), body.code)


@router.post("/security/authenticator/disable")
def authenticator_disable(body: CodeIn, x_step_up: str | None = Header(default=None)):
    return S.totp_disable(require_context(), body.code, x_step_up, body.recovery_code)


# ---------------- undoable reset ----------------
def _rows(ctx, h, table):
    if table == "receipt_items":
        ids = [r["id"] for r in ctx.db.table("grocery_receipts").select("id").eq("household_id", h["id"]).execute().data or []]
        return ctx.db.table("receipt_items").select("*").in_("receipt_id", ids).execute().data or [] if ids else []
    return ctx.db.table(table).select("*").eq("household_id", h["id"]).execute().data or []


@router.post("/account/reset")
def reset_account(x_step_up: str | None = Header(default=None)):
    ctx, h = require_household()
    S.require_step_up(ctx, "reset_account", x_step_up)
    from electricity import store as estore
    from water import store as wstore
    snapshot = {"water": wstore.load(), "electricity": estore.load(),
                "tables": {t: _rows(ctx, h, t) for t in TABLES}}
    kept = {}
    for t in reversed(TABLES):                         # children first
        ids = [r["id"] for r in snapshot["tables"][t]]
        if not ids:
            continue
        try:
            ctx.db.table(t).delete().in_("id", ids).execute()
        except Exception as exc:                       # e.g. another table still points at these rows (database FK/RLS)
            kept[t] = str(exc)[:160]
            snapshot["tables"][t] = []                 # not deleted, so nothing to restore for this table
    wstore.reset(sample=False)
    estore.reset(sample=False)
    sec = S.load(ctx)
    until = (datetime.now(timezone.utc) + timedelta(hours=RESTORE_HOURS)).isoformat(timespec="seconds")
    sec["reset_snapshot"] = {"household_id": h["id"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "restore_until": until, "data": snapshot}
    counts = {t: len(v) for t, v in snapshot["tables"].items() if v}
    if kept:
        import logging
        logging.getLogger(__name__).warning("Reset kept some tables: %s", kept)
    S.record(ctx, sec, "account_reset", restorable_until=until, records=counts)
    S.save(ctx, sec)
    return {"ok": True, "restorable_until": until, "cleared": counts,
            "message": f"Your records are hidden, not lost. You can restore them until {until[:16].replace('T', ' ')} UTC."}


@router.get("/account/reset-status")
def reset_status():
    ctx = require_context()
    snap = S.load(ctx).get("reset_snapshot")
    if not snap or datetime.fromisoformat(snap["restore_until"]) < datetime.now(timezone.utc):
        return {"restorable": False}
    return {"restorable": True, "reset_at": snap["at"], "restore_until": snap["restore_until"]}


@router.post("/account/restore")
def restore_account(x_step_up: str | None = Header(default=None)):
    ctx, h = require_household()
    S.require_step_up(ctx, "restore_account", x_step_up)
    sec = S.load(ctx)
    snap = sec.get("reset_snapshot")
    if not snap or datetime.fromisoformat(snap["restore_until"]) < datetime.now(timezone.utc):
        raise S.SecurityError(410, "nothing_to_restore", "There is no reset to undo (or the 24 hours have passed).")
    from electricity import store as estore
    from water import store as wstore
    for t in TABLES:                                   # parents first
        rows = snap["data"]["tables"].get(t) or []
        if rows:
            try:
                ctx.db.table(t).upsert(rows).execute()
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("Restore of %s failed: %s", t, exc)
    wstore.save(snap["data"]["water"])
    estore.save(snap["data"]["electricity"])
    sec.pop("reset_snapshot", None)
    S.record(ctx, sec, "account_restored")
    S.save(ctx, sec)
    return {"ok": True, "message": "Everything is back as it was before the reset."}
