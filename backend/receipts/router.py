import json
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from postgrest.exceptions import APIError
from pydantic import BaseModel, Field

from core.auth import HouseholdContext, get_household_context
from core.errors import db_error
from core.llm import LLMUnavailable, gemini_generate, image_part
from food_recognition.service import ImageRejected, MAX_BYTES, detect_media_type

from .logic import (GROCERY_PROMPT, OCR_PROMPT, NON_FOOD, food_total, normalize_receipt,
                    source_identifier_for)

router = APIRouter(prefix="/receipts", tags=["receipts"])


class ReceiptItem(BaseModel):
    original_name: str | None = None
    normalized_name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str
    line_total: float | None = Field(default=None, ge=0)
    category: str | None = None  # "food" from /receipts/parse


class ReceiptConfirm(BaseModel):
    source_identifier: str = Field(min_length=1)
    retailer: str | None = None
    receipt_date: date | None = None
    total: float = Field(ge=0)
    items: list[ReceiptItem] = Field(min_length=1)


@router.post("/parse")
def parse_receipt(image: UploadFile = File(...),
                  ctx: HouseholdContext = Depends(get_household_context)):
    """Read a receipt photo. Nothing is saved: the app shows the result for the
    user to correct, then calls /receipts/confirm."""
    data = image.file.read(MAX_BYTES + 1)
    try:
        mime = detect_media_type(data)
    except ImageRejected as exc:
        raise HTTPException(422, detail={"code": "bad_image", "message": str(exc)})

    try:
        text = gemini_generate([image_part(data, mime), OCR_PROMPT], json_output=False)
        grocery = json.loads(gemini_generate([GROCERY_PROMPT.format(extracted_text=text)]))
    except LLMUnavailable:
        raise HTTPException(503, detail={"code": "ai_unavailable",
                                         "message": "Receipt reading is unavailable. Try again shortly."})
    except json.JSONDecodeError:
        raise HTTPException(502, detail={"code": "bad_ai_reply",
                                         "message": "Could not read the receipt. Try a clearer photo."})

    items, rejected = normalize_receipt(grocery)
    return {
        "source_identifier": source_identifier_for(data),
        "retailer": grocery.get("store_name"),
        "receipt_date": grocery.get("receipt_date"),
        "total": food_total(items),                     # food only: send this to /confirm
        "receipt_total": grocery.get("receipt_total"),  # whole receipt, for display
        "currency": "MUR",
        "items": items,
        "excluded_non_food": [r["item"].get("original_name") or r["item"].get("normalized_name")
                              for r in rejected if r["reason"] == "not food"],
        "rejected_items": rejected,
        "uncertain_parts": grocery.get("uncertain_parts", []),
        "needs_confirmation": True,
    }


@router.post("/confirm")
def confirm_receipt(body: ReceiptConfirm, ctx: HouseholdContext = Depends(get_household_context)):
    """Save a reviewed receipt with her confirm_grocery_receipt function.
    Sending the same source_identifier again returns the same receipt and
    does not add to the pantry twice. Non-food lines are never saved."""
    food_items = [i for i in body.items
                  if (i.category or "").strip().lower() not in NON_FOOD]
    if not food_items:
        raise HTTPException(422, detail={"code": "no_food_items",
                                         "message": "No food items to save on this receipt."})
    total = body.total
    if len(food_items) < len(body.items):
        # Lines were dropped here, so the total sent by the app may include them.
        total = round(sum(i.line_total or 0 for i in food_items), 2)
    try:
        receipt_id = ctx.db.rpc("confirm_grocery_receipt", {
            "p_household_id": ctx.household_id,
            "p_source_identifier": body.source_identifier,
            "p_retailer": body.retailer,
            "p_receipt_date": body.receipt_date.isoformat() if body.receipt_date else None,
            "p_total": total,
            "p_items": [i.model_dump(exclude={"category"}) for i in food_items],
        }).execute().data
    except APIError as exc:
        raise db_error(exc)
    return {"receipt_id": receipt_id}
