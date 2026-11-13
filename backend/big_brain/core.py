"""Big Brain functions from Manvi's notebook (research/big_brain/athenav2_(with_ai_layer).py),
moved into the backend with the same names, inputs and outputs (LiveBetter_report_big_brain, section 4).

Changes at integration, all marked "INTEGRATION":
  - the database client is passed in (the logged-in user's Supabase client, or the local stand-in),
    instead of a global Colab client, so row-level security applies;
  - water and electricity status also count the modules' own confirmed bills, not only utility_bills;
  - combine_big_brain_actions keeps the module's confidence/assumptions/kind for the unified ranking.
"""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

ALLOWED_MODULES = {"food", "water", "electricity"}
CONFIDENCE = {"high", "medium", "low"}


def collect_household_data(db, household_id, module_bills=None):
    def fetch(table, filters=None):
        query = db.table(table).select("*")
        for column, value in (filters or {}).items():
            query = query.eq(column, value)
        return query.limit(1000).execute().data or []

    households = fetch("households", {"id": household_id})
    if not households:
        raise ValueError("Household not found")
    bills = fetch("utility_bills", {"household_id": household_id})
    readings = fetch("meter_readings", {"household_id": household_id})
    receipts = fetch("grocery_receipts", {"household_id": household_id})
    receipt_items = []
    for receipt in receipts:
        receipt_items.extend(fetch("receipt_items", {"receipt_id": receipt["id"]}))
    pantry = fetch("pantry_items", {"household_id": household_id})
    actions = fetch("household_actions", {"household_id": household_id})
    activity = fetch("activity_logs", {"household_id": household_id})
    module_bills = module_bills or {}
    return {
        "household": households[0],
        "water": {"bills": [b for b in bills if str(b["kind"]).lower() == "water"],
                  "readings": [r for r in readings if str(r["kind"]).lower() == "water"],
                  "module_bills": module_bills.get("water", [])},            # INTEGRATION
        "electricity": {"bills": [b for b in bills if str(b["kind"]).lower() == "electricity"],
                        "readings": [r for r in readings if str(r["kind"]).lower() == "electricity"],
                        "module_bills": module_bills.get("electricity", [])},  # INTEGRATION
        "food": {"receipts": receipts, "receipt_items": receipt_items, "pantry": pantry},
        "actions": actions,
        "activity_logs": activity,
    }


def verify_household_data(data):
    issues, verified_receipts, possible_duplicates = [], [], []
    items_by_receipt = defaultdict(list)
    for item in data["food"]["receipt_items"]:
        items_by_receipt[item["receipt_id"]].append(item)
    for receipt in data["food"]["receipts"]:
        receipt_items = items_by_receipt[receipt["id"]]
        try:
            expected = Decimal(str(receipt["total"]))
            calculated = sum((Decimal(str(i["line_total"])) for i in receipt_items), Decimal("0"))
        except (InvalidOperation, TypeError, KeyError):
            issues.append({"receipt_id": receipt["id"], "issue": "Invalid or missing numerical value"})
            continue
        difference = abs(expected - calculated)
        if difference <= Decimal("0.05"):
            verified_receipts.append(receipt["id"])
        else:
            issues.append({"receipt_id": receipt["id"], "issue": "Receipt total mismatch", "expected": str(expected),
                           "calculated": str(calculated), "difference": str(difference)})
    seen = {}
    for receipt in data["food"]["receipts"]:
        key = (str(receipt.get("retailer", "")).strip().lower(), receipt.get("receipt_date"), str(receipt.get("total")))
        if key in seen:
            possible_duplicates.append({"receipt_id": receipt["id"], "possible_duplicate_of": seen[key]})
        else:
            seen[key] = receipt["id"]

    def status(u):                                                             # INTEGRATION: + module bills
        d = data[u]
        return "available" if d["bills"] or d["readings"] or d.get("module_bills") else "insufficient_data"

    return {"verified_receipts": verified_receipts, "issues": issues, "possible_duplicates": possible_duplicates,
            "water_status": status("water"), "electricity_status": status("electricity")}


def build_decision_context(data, verification):
    pantry = data["food"]["pantry"]
    return {
        "household": {"members": data["household"]["members"], "currency": data["household"]["currency"],
                      "budget_goals": data["household"]["budget_goals"],
                      "preferences": data["household"]["preferences"]},
        "food": {"receipt_count": len(data["food"]["receipts"]),
                 "possible_duplicate_count": len(verification["possible_duplicates"]),
                 "pantry_item_count": len(pantry),
                 "missing_expiry_count": sum(p.get("expiry_date") is None for p in pantry)},
        "water": {"status": verification["water_status"],
                  "bill_count": max(len(data["water"]["bills"]), len(data["water"].get("module_bills", []))),
                  "reading_count": len(data["water"]["readings"])},
        "electricity": {"status": verification["electricity_status"],
                        "bill_count": max(len(data["electricity"]["bills"]),
                                          len(data["electricity"].get("module_bills", []))),
                        "reading_count": len(data["electricity"]["readings"])},
    }


def generate_action_candidates(context):
    actions = []
    food = context["food"]
    if food["possible_duplicate_count"] > 0:
        actions.append({"id": "review_duplicate_receipts", "module": "food",
                        "title": "Review possible duplicate receipts",
                        "evidence": {"possible_duplicate_count": food["possible_duplicate_count"]},
                        "impact": 3, "urgency": 3, "confidence": 3})
    if food["missing_expiry_count"] > 0:
        actions.append({"id": "complete_expiry_tracking", "module": "food",
                        "title": "Add verified pantry expiry dates",
                        "evidence": {"missing_expiry_count": food["missing_expiry_count"]},
                        "impact": 2, "urgency": 2, "confidence": 3})
    for module in ["water", "electricity"]:
        utility = context[module]
        if utility["status"] == "insufficient_data":
            actions.append({"id": f"collect_{module}_data", "module": module,
                            "title": f"Provide {module} billing or meter data",
                            "evidence": {"bill_count": utility["bill_count"], "reading_count": utility["reading_count"]},
                            "impact": 2, "urgency": 2, "confidence": 3})
    return actions


def rank_actions(actions):
    ranked = [{**a, "priority_score": round(0.40 * a["impact"] + 0.35 * a["urgency"] + 0.25 * a["confidence"], 2)}
              for a in actions]
    return sorted(ranked, key=lambda x: (-x["priority_score"], x["id"]))


def validate_domain_recommendation(rec):
    required = ["module", "action_id", "title", "estimated_savings_mur", "confidence", "evidence", "assumptions"]
    if not isinstance(rec, dict):
        raise ValueError("Recommendation must be an object")
    for f in required:
        if f not in rec:
            raise ValueError(f"Missing field: {f}")
    if rec["module"] not in ALLOWED_MODULES:
        raise ValueError("Invalid module")
    for f in ["action_id", "title"]:
        if not isinstance(rec[f], str) or not rec[f].strip():
            raise ValueError(f"Invalid {f}")
    if rec["confidence"] not in CONFIDENCE:
        raise ValueError("Invalid confidence")
    if not isinstance(rec["evidence"], dict):
        raise ValueError("Evidence must be an object")
    if not isinstance(rec["assumptions"], dict):
        raise ValueError("Assumptions must be an object")
    savings = rec["estimated_savings_mur"]
    if savings is not None:
        if isinstance(savings, bool):
            raise ValueError("Invalid savings value")
        try:
            amount = Decimal(str(savings))
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid savings value")
        if not amount.is_finite() or amount < 0:
            raise ValueError("Savings must be finite and non-negative")
    return True


def collect_domain_recommendations(food_results=None, water_results=None, electricity_results=None):
    modules = {"food": food_results or [], "water": water_results or [], "electricity": electricity_results or []}
    combined, seen = [], set()
    for module, recommendations in modules.items():
        for rec in recommendations:
            validate_domain_recommendation(rec)
            if rec["module"] != module:
                raise ValueError("Module mismatch")
            key = (module, rec["action_id"])
            if key in seen:
                raise ValueError("Duplicate action ID")
            seen.add(key)
            combined.append(rec)
    return combined


def combine_big_brain_actions(big_brain_actions, domain_recommendations):
    combined = []
    for a in big_brain_actions:
        combined.append({"source": "big_brain", "module": a["module"], "action_id": a["id"], "title": a["title"],
                         "priority_score": a["priority_score"], "estimated_savings_mur": None,
                         "confidence": {3: "high", 2: "medium", 1: "low"}.get(a["confidence"], "medium"),
                         "evidence": a["evidence"], "assumptions": {}, "kind": "data_quality",
                         "explanation": a.get("explanation")})
    for a in domain_recommendations:
        combined.append({"source": "domain_module", "module": a["module"], "action_id": a["action_id"],
                         "title": a["title"], "priority_score": a.get("priority_score"),
                         "estimated_savings_mur": a["estimated_savings_mur"], "confidence": a["confidence"],
                         "evidence": a["evidence"], "assumptions": a["assumptions"],
                         "kind": a.get("kind", "action"), "status": a.get("status"),          # INTEGRATION
                         "detail": a.get("detail"),
                         "explanation": a.get("explanation")})
    return combined


def build_integrated_dashboard(household_id, context, actions, module_status=None):
    return {"status": "success", "household_id": household_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "household": context["household"],
            "module_status": module_status or {
                "food": "data_available" if context["food"]["receipt_count"] or context["food"]["pantry_item_count"]
                else "insufficient_data",
                "water": "data_available" if context["water"]["status"] == "available" else "insufficient_data",
                "electricity": "data_available" if context["electricity"]["status"] == "available"
                else "insufficient_data"},
            "actions": actions, "action_count": len(actions)}
