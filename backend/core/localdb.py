"""Local stand-in for Supabase, used when SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY are not set.

Why: the app must also run on a laptop with no keys and no network (blueprint: "Demo network fails ->
prepared safe sample data and tested local/online fallback"), and the integration tests need a real
database behaviour. It copies the small part of the supabase-py API the backend uses
(table().select().eq().gt().order().limit().execute(), insert, update, upsert, delete, rpc) and the three
SQL functions of sql/01 + sql/02 in Python, with the same rules:
  confirm_grocery_receipt : first confirmation wins, pantry added once, activity logged
  lb_confirm_cooking      : ingredients deducted once per operation id, never below zero, water skipped
  lb_save_ai_recipe       : AI recipe saved as a private, pending draft
Data is kept in backend/.localdata/<user>.json (git-ignored). It is for one demo account, not production.
"""
import copy
import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timezone

from postgrest.exceptions import APIError

ROOT = os.environ.get("LIVEBETTER_LOCAL_DATA", os.path.join(os.path.dirname(__file__), "..", ".localdata"))
_LOCK = threading.RLock()
UNIQUE = {
    "households": [("id",)],
    "pantry_items": [("household_id", "ingredient_name", "unit")],
    "grocery_receipts": [("household_id", "source_identifier")],
    "module_state": [("household_id", "module")],
    "cooking_operations": [("id",)],
}
UNITS = {"kg", "g", "l", "ml", "piece"}
NOT_TRACKED = {"water", "tap water", "eau"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _err(message, code="P0001"):
    return APIError({"message": message, "code": code, "hint": None, "details": None})


class _Resp:
    def __init__(self, data):
        self.data = data


class LocalDB:
    """One JSON file per local user. `user_id` plays the role of auth.uid()."""

    def __init__(self, user_id, path=None, seed=True):
        self.user_id = user_id
        os.makedirs(ROOT, exist_ok=True)
        self.path = path or os.path.join(ROOT, re.sub(r"[^A-Za-z0-9_-]", "_", user_id) + ".json")
        with _LOCK:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as fh:
                    self.tables = json.load(fh)
            else:
                self.tables = {}
                if seed:
                    from .local_seed import seed_recipes
                    seed_recipes(self)
                self._save()

    # ---------- supabase-like API ----------
    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        fn = {"confirm_grocery_receipt": self._confirm_grocery_receipt,
              "lb_confirm_cooking": self._confirm_cooking,
              "lb_save_ai_recipe": self._save_ai_recipe}.get(name)
        if fn is None:
            raise _err(f"Function {name} does not exist", "42883")
        db = self

        class _Call:
            def execute(self_inner):
                with _LOCK:
                    before = copy.deepcopy(db.tables)
                    try:
                        out = fn(**params)
                    except Exception:
                        db.tables = before                 # all-or-nothing, like a SQL transaction
                        raise
                    db._save()
                    return _Resp(out)
        return _Call()

    # ---------- storage ----------
    def rows(self, name):
        return self.tables.setdefault(name, [])

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.tables, fh, indent=1, default=str)
        os.replace(tmp, self.path)

    def _insert(self, name, row, on_conflict=None, upsert=False):
        row = {k: (v.isoformat() if isinstance(v, (date, datetime)) else v) for k, v in row.items()}
        row.setdefault("id", str(uuid.uuid4()))
        row.setdefault("created_at", _now())
        keys = [tuple(on_conflict.split(","))] if on_conflict else UNIQUE.get(name, [("id",)])
        for key in keys:
            key = tuple(k.strip() for k in key)
            for existing in self.rows(name):
                if all(existing.get(k) == row.get(k) for k in key) and all(row.get(k) is not None for k in key):
                    if upsert:
                        existing.update({k: v for k, v in row.items() if k not in ("id", "created_at")})
                        return existing
                    raise _err(f'duplicate key value violates unique constraint on {name} {key}', "23505")
        self.rows(name).append(row)
        return row

    def _owned(self, household_id):
        return any(h["id"] == household_id and h.get("owner_id") == self.user_id for h in self.rows("households"))

    # ---------- SQL functions (Python copies of sql/01 and sql/02) ----------
    def _confirm_grocery_receipt(self, p_household_id, p_source_identifier, p_retailer, p_receipt_date,
                                 p_total, p_items):
        if not self._owned(p_household_id):
            raise _err("Unauthorized household", "42501")
        if not p_source_identifier or not str(p_source_identifier).strip() or p_total is None or p_total < 0 \
                or not isinstance(p_items, list) or not p_items:
            raise _err("Invalid receipt input", "22023")
        for r in self.rows("grocery_receipts"):
            if r["household_id"] == p_household_id and r["source_identifier"] == p_source_identifier:
                return r["id"]                            # first confirmation wins
        receipt = self._insert("grocery_receipts", {
            "household_id": p_household_id, "source_identifier": p_source_identifier, "retailer": p_retailer,
            "receipt_date": p_receipt_date, "total": float(p_total), "currency": "MUR"})
        for item in p_items:
            if not isinstance(item, dict):
                raise _err("Each item must be a JSON object", "22023")
            name = str(item.get("normalized_name") or "").strip().lower()
            unit = str(item.get("unit") or "").strip().lower()
            qty, price = item.get("quantity"), item.get("line_total")
            try:
                qty = float(qty)
                price = None if price is None else float(price)
            except (TypeError, ValueError):
                raise _err("Invalid item name, unit, quantity or price", "22023")
            if not name or unit not in UNITS or (price is not None and price < 0):
                raise _err("Invalid item name, unit, quantity or price", "22023")
            if qty <= 0 or qty > 999999999:
                raise _err("Item quantity out of range", "22023")
            self._insert("receipt_items", {"receipt_id": receipt["id"],
                                           "original_name": (item.get("original_name") or name).strip() or name,
                                           "normalized_name": name, "quantity": qty, "unit": unit, "line_total": price})
            pantry = next((p for p in self.rows("pantry_items") if p["household_id"] == p_household_id
                           and p["ingredient_name"] == name and p["unit"] == unit), None)
            if pantry:
                pantry["quantity"] = round(float(pantry["quantity"]) + qty, 3)
                pantry["available"], pantry["updated_at"] = True, _now()
            else:
                pantry = self._insert("pantry_items", {"household_id": p_household_id, "ingredient_name": name,
                                                       "quantity": qty, "unit": unit, "expiry_date": None,
                                                       "available": True, "updated_at": _now()})
            self._insert("pantry_events", {"household_id": p_household_id, "pantry_item_id": pantry["id"],
                                           "quantity_delta": qty, "reason": "receipt_purchase", "operation_id": None})
        self._insert("activity_logs", {"household_id": p_household_id, "event_type": "receipt_confirmed",
                                       "related_entity_id": receipt["id"],
                                       "details": {"total": float(p_total), "items": len(p_items)}})
        return receipt["id"]

    def _confirm_cooking(self, p_household_id, p_recipe_id, p_operation_id):
        if not self._owned(p_household_id):
            raise _err("Unauthorized household", "42501")
        recipe = next((r for r in self.rows("lb_recipes") if r["id"] == p_recipe_id and
                       (r.get("verification_status") == "verified" or r.get("household_id") == p_household_id)), None)
        if recipe is None:
            raise _err("Recipe not accessible")
        op = next((o for o in self.rows("cooking_operations") if o["id"] == p_operation_id), None)
        if op:
            if op["recipe_id"] != str(p_recipe_id):
                raise _err("Operation ID already used")
            return {"status": "already_confirmed", "operation_id": p_operation_id}
        self._insert("cooking_operations", {"id": p_operation_id, "household_id": p_household_id,
                                            "recipe_id": str(p_recipe_id)})
        needed = {}
        for ing in self.rows("lb_recipe_ingredients"):
            if ing["recipe_id"] == p_recipe_id and not ing.get("optional"):
                key = (ing["ingredient_name"].strip().lower(), (ing.get("unit") or "").strip().lower())
                needed[key] = needed.get(key, 0) + float(ing.get("quantity") or 0)
        if not needed:
            raise _err("Recipe has no required ingredients")
        deducted, skipped, count = [], [], 0
        for (name, unit), qty in sorted(needed.items()):
            if qty <= 0 or not unit:
                raise _err(f"Invalid quantity or unit for ingredient {name}")
            if name in NOT_TRACKED:
                skipped.append({"ingredient": name, "reason": "water is not tracked"})
                continue
            factor = {(unit, unit): 1, ("kg", "g"): 1000, ("g", "kg"): 0.001, ("l", "ml"): 1000, ("ml", "l"): 0.001}
            candidates = [p for p in self.rows("pantry_items") if p["household_id"] == p_household_id
                          and p["ingredient_name"].strip().lower() == name
                          and (unit, p["unit"].strip().lower()) in factor]
            candidates.sort(key=lambda p: (p["unit"].strip().lower() != unit, -float(p["quantity"])))
            if not candidates:
                skipped.append({"ingredient": name, "quantity": qty, "unit": unit, "reason": "not in pantry"})
                continue
            p = candidates[0]
            need = qty * factor[(unit, p["unit"].strip().lower())]
            if float(p["quantity"]) < need - 1e-9:
                raise _err(f"Insufficient ingredient: {name} (need {round(need, 3)} {p['unit']}, "
                           f"have {p['quantity']} {p['unit']})")
            p["quantity"] = round(float(p["quantity"]) - need, 3)
            p["available"], p["updated_at"] = p["quantity"] > 0, _now()
            self._insert("pantry_events", {"household_id": p_household_id, "pantry_item_id": p["id"],
                                           "quantity_delta": -need, "reason": "recipe_cooked",
                                           "operation_id": p_operation_id})
            deducted.append({"ingredient": name, "quantity": need, "unit": p["unit"]})
            count += 1
        self._insert("activity_logs", {"household_id": p_household_id, "event_type": "recipe_cooked",
                                       "related_entity_id": p_recipe_id,
                                       "details": {"operation_id": p_operation_id, "ingredients_deducted": count,
                                                   "deducted": deducted, "skipped": skipped,
                                                   "recipe_name": recipe["name"]}})
        return {"status": "confirmed", "operation_id": p_operation_id, "ingredients_deducted": count,
                "deducted": deducted, "skipped": skipped}

    def _save_ai_recipe(self, p_household_id, p_recipe):
        if not self._owned(p_household_id):
            raise _err("Unauthorized household", "42501")
        if not isinstance(p_recipe, dict):
            raise _err("Recipe must be a JSON object")
        name = (p_recipe.get("name") or p_recipe.get("recipe_name") or "").strip()
        ings = p_recipe.get("ingredients")
        instructions = p_recipe.get("instructions") or []
        if not name:
            raise _err("Recipe name is required")
        if not isinstance(ings, list) or not ings:
            raise _err("Recipe ingredients must be a non-empty array")
        if not isinstance(instructions, list):
            raise _err("Instructions must be an array")
        recipe = self._insert("lb_recipes", {
            "household_id": p_household_id, "name": name, "cuisine": p_recipe.get("cuisine") or "Mauritian",
            "description": p_recipe.get("description"), "servings": int(p_recipe.get("servings") or 4),
            "source_type": "ai_generated", "verification_status": "pending", "source_url": None,
            "youtube_url": None, "prep_minutes": p_recipe.get("prep_minutes"),
            "cook_minutes": p_recipe.get("cook_minutes"), "instructions": instructions})
        for ing in ings:
            self._insert("lb_recipe_ingredients", {
                "recipe_id": recipe["id"], "ingredient_name": ing.get("ingredient_name") or ing.get("name"),
                "quantity": ing.get("quantity"), "unit": ing.get("unit"), "optional": bool(ing.get("optional"))})
        return recipe["id"]


class _Query:
    def __init__(self, db, name):
        self.db, self.name = db, name
        self.filters, self.order_by, self.max_rows = [], [], None
        self.nested, self.op, self.payload, self.on_conflict = [], "select", None, None

    def select(self, cols="*", **_):
        self.nested = re.findall(r"(\w+)\(([^)]*)\)", cols or "")
        return self

    def _f(self, fn):
        self.filters.append(fn)
        return self

    def eq(self, c, v):
        return self._f(lambda r: str(r.get(c)) == str(v) if v is not None else r.get(c) is None)

    def neq(self, c, v):
        return self._f(lambda r: r.get(c) != v)

    def gt(self, c, v):
        return self._f(lambda r: r.get(c) is not None and float(r[c]) > float(v))

    def gte(self, c, v):
        return self._f(lambda r: r.get(c) is not None and str(r[c]) >= str(v) if isinstance(v, str) else
                       r.get(c) is not None and float(r[c]) >= float(v))

    def lte(self, c, v):
        return self._f(lambda r: r.get(c) is not None and str(r[c]) <= str(v) if isinstance(v, str) else
                       r.get(c) is not None and float(r[c]) <= float(v))

    def in_(self, c, values):
        values = {str(v) for v in values}
        return self._f(lambda r: str(r.get(c)) in values)

    def order(self, c, desc=False, **_):
        self.order_by.append((c, desc))
        return self

    def limit(self, n):
        self.max_rows = n
        return self

    def insert(self, payload, **_):
        self.op, self.payload = "insert", payload
        return self

    def upsert(self, payload, on_conflict=None, **_):
        self.op, self.payload, self.on_conflict = "upsert", payload, on_conflict
        return self

    def update(self, payload):
        self.op, self.payload = "update", payload
        return self

    def delete(self):
        self.op = "delete"
        return self

    def execute(self):
        with _LOCK:
            rows = self.db.rows(self.name)
            if self.op in ("insert", "upsert"):
                items = self.payload if isinstance(self.payload, list) else [self.payload]
                out = [copy.deepcopy(self.db._insert(self.name, dict(i), self.on_conflict, self.op == "upsert"))
                       for i in items]
                self.db._save()
                return _Resp(out)
            hit = [r for r in rows if all(f(r) for f in self.filters)]
            if self.op == "update":
                for r in hit:
                    r.update({k: (v.isoformat() if isinstance(v, (date, datetime)) else v)
                              for k, v in self.payload.items()})
                self.db._save()
                return _Resp(copy.deepcopy(hit))
            if self.op == "delete":
                self.db.tables[self.name] = [r for r in rows if r not in hit]
                self.db._save()
                return _Resp(copy.deepcopy(hit))
            for c, desc in reversed(self.order_by):
                hit = sorted(hit, key=lambda r: (r.get(c) is None, r.get(c) if r.get(c) is not None else ""),
                             reverse=desc)
            if self.max_rows is not None:
                hit = hit[: self.max_rows]
            out = copy.deepcopy(hit)
            for child, _cols in self.nested:
                fk = "recipe_id" if child == "lb_recipe_ingredients" else f"{self.name.rstrip('s')}_id"
                for r in out:
                    r[child] = [copy.deepcopy(x) for x in self.db.rows(child) if x.get(fk) == r["id"]]
            return _Resp(out)
