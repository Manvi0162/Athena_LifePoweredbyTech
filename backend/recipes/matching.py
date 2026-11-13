"""Ingredient matching.

Part 1 is copied from the notebook's recipe engine (cell 3): canonical(),
quantity_in_base() and evaluate_recipe(), used for "can I cook this now?".
Part 2 is the food-photo search: which recipes use these ingredients.
"""

import re

# ---------- Part 1: notebook recipe engine, cell 3 (unchanged) ----------
ALIASES = {
    'brinjal':'eggplant', 'aubergine':'eggplant', 'bringelle':'eggplant',
    'tomatoes':'tomato', 'onions':'onion', 'carrots':'carrot', 'eggs':'egg',
    'pommes de terre':'potato', 'pomme de terre':'potato',
    'ail':'garlic', 'gingembre':'ginger', 'riz':'rice'
}
FACTORS = {'kg':(1000,'mass'),'g':(1,'mass'),
           'l':(1000,'volume'),'ml':(1,'volume'),'piece':(1,'count')}

def canonical(name):
    name = re.sub(r'\s+', ' ', str(name).strip().lower())
    return ALIASES.get(name, name)

def quantity_in_base(amount, unit):
    if amount is None or unit not in FACTORS: return None
    try:
        number = float(amount)
        if number < 0: return None
        factor, family = FACTORS[unit]
        return number * factor, family
    except (ValueError, TypeError):
        return None

def evaluate_recipe(recipe, pantry):
    stock = {}
    for item in pantry:
        stock.setdefault(canonical(item['ingredient_name']), []).append(item)
    ingredients = recipe.get('lb_recipe_ingredients', recipe.get('ingredients', []))
    required = [x for x in ingredients if not x.get('optional', False)]
    if not required:
        return {'recipe':recipe,'coverage':0,'missing':[],
                'uncertain':[],'cook_now':False}
    covered, missing, uncertain = 0, [], []
    for ing in required:
        name = canonical(ing['ingredient_name'])
        candidates = stock.get(name, [])
        if not candidates:
            missing.append(ing['ingredient_name']); continue
        need = quantity_in_base(ing.get('quantity'), ing.get('unit'))
        if need is None:
            uncertain.append(ing['ingredient_name']); continue
        amounts = [quantity_in_base(x.get('quantity'),x.get('unit')) for x in candidates]
        comparable = [a[0] for a in amounts if a and a[1] == need[1]]
        if not comparable:
            uncertain.append(ing['ingredient_name'])
        elif sum(comparable) >= need[0]:
            covered += 1
        else:
            missing.append(ing['ingredient_name'])
    return {'recipe':recipe,'coverage':round(covered/len(required),3),
            'missing':missing,'uncertain':uncertain,
            'cook_now':covered == len(required) and not missing and not uncertain}


# ---------- Part 2: food-photo search (same as FOOD PHOTO CELL 4) ----------
PHOTO_ALIASES = {
    'prawn': 'shrimp', 'prawns': 'shrimp', 'shrimps': 'shrimp',
    'crevette': 'shrimp', 'crevettes': 'shrimp',
    'poulet': 'chicken', 'poisson': 'fish', 'oeuf': 'egg', 'oeufs': 'egg',
}


def photo_words(name):
    """Canonical name -> set of singular words, e.g. 'Chicken Thighs' -> {'chicken', 'thigh'}."""
    name = canonical(name)
    name = PHOTO_ALIASES.get(name, name)
    words = set()
    for word in re.findall(r'[a-z]+', name):
        word = PHOTO_ALIASES.get(word, word)
        if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
            word = word[:-1]
        words.add(word)
    return words


def uses_ingredient(recipe_ingredient, photo_ingredient):
    """True if every word of the photo ingredient appears in the recipe ingredient.
    'chicken' matches 'chicken thigh'; 'tomato sauce' does not match 'tomato'."""
    wanted = photo_words(photo_ingredient)
    return bool(wanted) and wanted <= photo_words(recipe_ingredient)


# Same list lb_confirm_cooking v2 skips: never "to buy", never deducted.
NOT_TRACKED = {'water', 'tap water', 'eau'}


def match_recipes(recipes, wanted, pantry_names):
    rows = []
    for recipe in recipes:
        ingredients = recipe.get('lb_recipe_ingredients') or []
        names = [ing['ingredient_name'] for ing in ingredients]
        matched = [w for w in wanted if any(uses_ingredient(n, w) for n in names)]
        if not matched:
            continue
        others = [ing['ingredient_name'] for ing in ingredients
                  if not ing.get('optional', False)
                  and canonical(ing['ingredient_name']) not in NOT_TRACKED
                  and not any(uses_ingredient(ing['ingredient_name'], w) for w in wanted)]
        in_pantry = [n for n in others if canonical(n) in pantry_names]
        to_buy = [n for n in others if canonical(n) not in pantry_names]
        rows.append({'recipe': recipe, 'matched': matched,
                     'in_pantry': in_pantry, 'to_buy': to_buy})
    # Most photo ingredients used first, then fewest to buy, then verified recipes first.
    rows.sort(key=lambda r: (-len(r['matched']), len(r['to_buy']),
                             r['recipe'].get('verification_status') != 'verified'))
    return rows
