"""Food module recommendations in the Big Brain input format (LiveBetter_report_big_brain, section 3).

Calculated here, in the food module, so Big Brain only combines and ranks them:
  use_expiring_items : pantry items that expire within 3 days. Value at risk = latest purchase price per unit
                       (confirmed receipt lines) x quantity left. null if no price was ever recorded.
  cook_from_pantry   : verified recipes that can be cooked now with the pantry (notebook evaluate_recipe()).
                       No saving is claimed (we do not know what the household would otherwise buy).
"""
from datetime import date, timedelta

from .matching import canonical, evaluate_recipe

EXPIRY_DAYS = 3


def _value_at_risk(item, receipt_items):
    lines = [r for r in receipt_items if canonical(r["normalized_name"]) == canonical(item["ingredient_name"])
             and r["unit"] == item["unit"] and r.get("line_total") is not None and float(r["quantity"]) > 0]
    if not lines:
        return None
    last = sorted(lines, key=lambda r: r.get("created_at") or "")[-1]
    return round(float(last["line_total"]) / float(last["quantity"]) * float(item["quantity"]), 2)


def food_recommendations(pantry, receipt_items, recipes, today=None):
    today = today or date.today()
    out = []
    soon = []
    for p in pantry:
        if not p.get("available") or float(p.get("quantity") or 0) <= 0 or not p.get("expiry_date"):
            continue
        exp = date.fromisoformat(str(p["expiry_date"])[:10])
        if exp <= today + timedelta(days=EXPIRY_DAYS):
            soon.append((exp, p))
    if soon:
        soon.sort(key=lambda x: x[0])
        values = [_value_at_risk(p, receipt_items) for _, p in soon]
        known = [v for v in values if v is not None]
        out.append({
            "module": "food", "action_id": "use_expiring_items",
            "title": "Use soon: " + ", ".join(p["ingredient_name"] for _, p in soon[:4]),
            "estimated_savings_mur": round(sum(known), 2) if known else None,
            "confidence": "medium" if known else "low",
            "evidence": {"items": [{"name": p["ingredient_name"], "quantity": p["quantity"], "unit": p["unit"],
                                    "expiry_date": str(e), "value_at_risk_mur": v} for (e, p), v in zip(soon, values)],
                         "method": "latest confirmed purchase price per unit x quantity left"},
            "assumptions": {"period": f"next {EXPIRY_DAYS} days", "currency": "MUR",
                            "note": "Value at risk only for items with a recorded purchase price; "
                                    "a missing expiry date is not treated as expired."},
            "kind": "alert"})
    pantry_ok = [p for p in pantry if p.get("available") and float(p.get("quantity") or 0) > 0]
    cookable = []
    for r in recipes:
        if r.get("verification_status") != "verified":
            continue
        a = evaluate_recipe(r, pantry_ok)
        if a["cook_now"]:
            cookable.append(r)
    if cookable:
        r = cookable[0]
        out.append({
            "module": "food", "action_id": "cook_from_pantry",
            "title": f"Cook {r['name']} with what you already have",
            "estimated_savings_mur": None, "confidence": "high",
            "evidence": {"recipe_id": r["id"], "recipe": r["name"], "cookable_recipes": len(cookable),
                         "method": "every required ingredient is in the pantry in enough quantity"},
            "assumptions": {"period": "today", "currency": "MUR",
                            "note": "No money saving is claimed; it avoids buying what you already have."},
            "kind": "action"})
    return out
