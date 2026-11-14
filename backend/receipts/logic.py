"""Receipt reading. Prompts and normalize_receipt are copied from the notebook."""

import hashlib
from decimal import Decimal, InvalidOperation

# Notebook cell 8 (receipt OCR)
OCR_PROMPT = ("Extract all text from this grocery receipt. "
              "Preserve product names, quantities, prices "
              "and totals. Return plain text.")

# Notebook cell 9 (grocery extraction), unchanged
GROCERY_PROMPT = """
You are a grocery receipt extraction system for Mauritius.

Extract structured grocery information from this OCR text:

{extracted_text}

Return a JSON object with:
- store_name
- receipt_date (YYYY-MM-DD or null)
- currency ("MUR")
- receipt_total
- items (array)
- uncertain_parts (array)

For each item include:
- original_name: exact product text
- normalized_name: understandable product name
- quantity: number of purchased units
- unit: kg, g, ml, l, piece, or unknown
- package_size: number or null
- package_unit: unit of package size or null
- line_total: price in Mauritian rupees or null
- confidence: high, medium, or low
- category: "food" for anything eaten or drunk (including tea, coffee, drinks,
  spices, cooking oil, sugar, baby food), or "non_food" for everything else
  (toiletries, toothpaste, cleaning products, batteries, electronics, cables,
  stationery, bags, kitchen tools, pet supplies)

Rules:
1. Never invent products or prices.
2. Preserve duplicate receipt lines.
3. Do not confuse product quantity with package size.
4. Do not assume a price is a unit price.
5. Mark ambiguous products as low confidence.
6. Do not include VAT summaries as products.
7. Use null when a value cannot be determined.
8. Return only valid JSON.
9. Classify every line as food or non_food. Do not drop any line yourself.
"""

ALLOWED_UNITS = {"kg", "g", "l", "ml", "piece"}
NON_FOOD = {"non_food", "non-food", "nonfood", "non food"}


def is_non_food(product) -> bool:
    """Only lines the AI explicitly labels non_food are excluded. A missing
    label is kept, so the user can decide during review."""
    return str(product.get("category") or "").strip().lower() in NON_FOOD


def source_identifier_for(image_bytes: bytes) -> str:
    """Hash of the photo itself. The notebook hashed the OCR text, which changes
    between runs, so the same receipt could be saved twice (as her comment notes:
    'Use the original receipt image hash when available')."""
    return hashlib.sha256(image_bytes).hexdigest()


def normalize_receipt(grocery_data):
    """Notebook cell 19. Changes: skipped items are returned (with a reason)
    instead of printed, and non-food lines are excluded so they are never saved."""
    items, rejected = [], []

    for product in grocery_data.get("items", []):
        if is_non_food(product):
            rejected.append({"item": product, "reason": "not food"})
            continue

        name = str(
            product.get("normalized_name")
            or product.get("original_name")
            or ""
        ).strip().lower()

        unit = str(
            product.get("unit") or "unknown"
        ).strip().lower()

        try:
            quantity = Decimal(
                str(product.get("quantity"))
            )
        except (InvalidOperation, TypeError):
            quantity = Decimal("0")

        raw_price = product.get("line_total")
        try:
            price = (
                None if raw_price is None
                else float(Decimal(str(raw_price)))
            )
        except (InvalidOperation, TypeError):
            price = None

        if not name or quantity <= 0:
            rejected.append({"item": product, "reason": "needs review"})
            continue

        if unit not in ALLOWED_UNITS:
            rejected.append({"item": product, "reason": "unsupported unit"})
            continue

        if price is not None and price < 0:
            rejected.append({"item": product, "reason": "invalid price"})
            continue

        items.append({
            "original_name": str(
                product.get("original_name") or name
            ),
            "normalized_name": name,
            "quantity": float(quantity),
            "unit": unit,
            "line_total": price,
            "category": "food"
        })

    return items, rejected


def food_total(items):
    """Sum of the kept (food) lines. Lines without a price are not counted."""
    return round(sum(i["line_total"] for i in items if i["line_total"] is not None), 2)
