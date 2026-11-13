from fastapi import APIRouter, Depends

from core.auth import HouseholdContext, get_household_context

router = APIRouter(tags=["household"])


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
