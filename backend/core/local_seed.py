"""Recipes for the LOCAL mode only (no Supabase keys).

With Supabase, recipes come from the team's lb_recipes table (UniTools dataset, CC BY-SA 4.0, loaded by
the food lead). Locally we only have these few illustrative recipes, the same ones the Expo demo mode
uses, so the pantry -> recipe -> cook flow can be shown offline. They are labelled as illustrative.
"""
LOCAL_RECIPES = [
    ("Vegetable Fried Rice", 20, [("rice", 0.2, "kg"), ("carrot", 1, "piece"), ("peas", 0.1, "kg"), ("onion", 1, "piece")],
     ["Cook the rice.", "Saute the chopped vegetables.", "Combine and season."]),
    ("Vegetable Omelette", 10, [("egg", 2, "piece"), ("onion", 1, "piece"), ("carrot", 1, "piece")],
     ["Whisk the eggs.", "Add finely chopped vegetables.", "Cook through."]),
    ("Rice & Peas", 25, [("rice", 0.2, "kg"), ("peas", 0.15, "kg")],
     ["Cook the rice and peas together.", "Season to taste."]),
]
SOURCE = "Illustrative local demo recipe (offline mode). The deployed app uses the UniTools dataset in Supabase."


def seed_recipes(db):
    for name, minutes, ings, steps in LOCAL_RECIPES:
        r = db._insert("lb_recipes", {"household_id": None, "name": name, "cuisine": "Demo", "description": SOURCE,
                                      "servings": 2, "source_type": "curated", "verification_status": "verified",
                                      "source_url": None, "youtube_url": None, "prep_minutes": 5,
                                      "cook_minutes": minutes, "instructions": steps})
        for ing, qty, unit in ings:
            db._insert("lb_recipe_ingredients", {"recipe_id": r["id"], "ingredient_name": ing, "quantity": qty,
                                                 "unit": unit, "optional": False})
