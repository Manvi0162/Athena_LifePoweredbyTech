from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field

from core.auth import HouseholdContext, get_household_context
from core.errors import db_error

router = APIRouter(tags=["household"])
UNITS = {"kg", "g", "l", "ml", "piece"}           # same units the SQL functions accept


@router.get("/household")
def household(ctx: HouseholdContext = Depends(get_household_context)):
    return ctx.household


@router.get("/pantry")
def pantry(ctx: HouseholdContext = Depends(get_household_context)):
    rows = (ctx.db.table("pantry_items")
            .select("id,ingredient_name,quantity,unit,expiry_date,available,updated_at")
            .eq("household_id", ctx.household_id)
            .order("ingredient_name").execute().data or [])
    return {"items": rows}


# ---- manual pantry changes (added at integration: the app's "Add item", "Edit", "Mark unavailable") ----
class PantryAdd(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    quantity: float = Field(ge=0, le=100000)
    unit: str
    expiry: date | None = None
    available: bool = True


class PantryEdit(BaseModel):
    id: str
    name: str | None = Field(default=None, min_length=1, max_length=80)
    quantity: float | None = Field(default=None, ge=0, le=100000)
    unit: str | None = None
    expiry: date | None = None
    available: bool | None = None


def _unit(u):
    u = (u or "").strip().lower()
    if u not in UNITS:
        raise HTTPException(422, detail={"code": "invalid_input",
                                         "message": f"Unit must be one of: {', '.join(sorted(UNITS))}"})
    return u


def _event(ctx, item_id, delta, reason, details):
    ctx.db.table("pantry_events").insert({"household_id": ctx.household_id, "pantry_item_id": item_id,
                                          "quantity_delta": delta, "reason": reason}).execute()
    ctx.db.table("activity_logs").insert({"household_id": ctx.household_id, "event_type": reason,
                                          "related_entity_id": item_id, "details": details}).execute()


@router.post("/pantry")
def add_item(body: PantryAdd, ctx: HouseholdContext = Depends(get_household_context)):
    """Add stock by hand (no purchase, so no grocery expense). Same name + unit adds to the existing line."""
    name, unit = body.name.strip().lower(), _unit(body.unit)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        existing = (ctx.db.table("pantry_items").select("id,quantity").eq("household_id", ctx.household_id)
                    .eq("ingredient_name", name).eq("unit", unit).limit(1).execute().data or [])
        if existing:
            item = existing[0]
            qty = round(float(item["quantity"]) + body.quantity, 3)
            ctx.db.table("pantry_items").update({
                "quantity": qty, "available": body.available and qty > 0, "updated_at": now,
                **({"expiry_date": body.expiry.isoformat()} if body.expiry else {})}).eq("id", item["id"]).execute()
            item_id = item["id"]
        else:
            row = ctx.db.table("pantry_items").insert({
                "household_id": ctx.household_id, "ingredient_name": name, "quantity": body.quantity, "unit": unit,
                "expiry_date": body.expiry.isoformat() if body.expiry else None,
                "available": body.available and body.quantity > 0}).execute().data[0]
            item_id = row["id"]
        _event(ctx, item_id, body.quantity, "manual_add", {"name": name, "quantity": body.quantity, "unit": unit})
    except APIError as exc:
        raise db_error(exc)
    return pantry(ctx)


@router.patch("/pantry")
def edit_item(body: PantryEdit, ctx: HouseholdContext = Depends(get_household_context)):
    """Correct an item, mark it unavailable or set its expiry date. The change is logged with its reason."""
    rows = (ctx.db.table("pantry_items").select("id,ingredient_name,quantity,unit,available")
            .eq("household_id", ctx.household_id).eq("id", body.id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(404, detail={"code": "not_found", "message": "Pantry item not found."})
    old = rows[0]
    change = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if body.name is not None:
        change["ingredient_name"] = body.name.strip().lower()
    if body.unit is not None:
        change["unit"] = _unit(body.unit)
    if body.quantity is not None:
        change["quantity"] = body.quantity
    if body.expiry is not None:
        change["expiry_date"] = body.expiry.isoformat()
    if body.available is not None:
        change["available"] = body.available
    if change.get("quantity", 1) == 0:
        change["available"] = False
    try:
        ctx.db.table("pantry_items").update(change).eq("id", body.id).execute()
        delta = round(float(change.get("quantity", old["quantity"])) - float(old["quantity"]), 3)
        reason = ("marked_unavailable" if body.available is False else
                  "marked_available" if body.available is True and not old["available"] else "manual_correction")
        _event(ctx, body.id, delta, reason, {"name": change.get("ingredient_name", old["ingredient_name"]),
                                             "fields": sorted(k for k in change if k != "updated_at")})
    except APIError as exc:
        raise db_error(exc)
    return pantry(ctx)
