"""AI recipe draft. Prompt and validation copied from the notebook's
recipe engine (cell 4, generate_recipe)."""

import json

from core.llm import gemini_generate

from .matching import FACTORS


def generate_recipe(pantry, servings=4, allergies=None, diet='none', must_use=None):
    if not pantry:
        raise ValueError('Pantry is empty. Confirm a grocery receipt first.')
    allergies = allergies or []
    prompt = f"""You are LiveBetter's Mauritian home-cooking assistant.
Create ONE practical Mauritian or Mauritian-inspired recipe using the available pantry.
Return a single JSON object with fields:
name, cuisine, description, servings, prep_minutes, cook_minutes,
ingredients (array of ingredient_name, quantity, unit, optional),
instructions (array of short strings).
Each ingredient must include a positive numeric quantity and unit if possible.
Allowed units: kg, g, l, ml, piece; null when unknown.
Include ALL required ingredients, even those absent from the pantry.
Label adaptations Mauritian-inspired. Never invent a recipe source or video URL.
Do not claim ingredients are available unless listed in pantry.
Avoid stated allergens, including hidden allergens in sauces and condiments.
Do not make unsupported health or nutrition claims.
Servings: {servings}. Diet: {diet}. Allergies: {json.dumps(allergies)}.
{('The recipe MUST use: ' + json.dumps(must_use, ensure_ascii=False) + ' (the item the user wants to use now).') if must_use else ''}
Pantry: {json.dumps(pantry, ensure_ascii=False)}"""
    result = json.loads(gemini_generate([prompt], json_output=True))
    if not isinstance(result, dict) or not str(result.get('name','')).strip():
        raise ValueError('Gemini returned an invalid recipe name')
    ingredients = result.get('ingredients')
    if not isinstance(ingredients,list) or not ingredients:
        raise ValueError('Gemini returned no ingredients')
    if not isinstance(result.get('instructions'),list) or not result['instructions']:
        raise ValueError('Gemini returned no instructions')
    for ing in ingredients:
        if not isinstance(ing,dict) or not str(ing.get('ingredient_name','')).strip():
            raise ValueError('Invalid ingredient')
        if ing.get('unit') not in (*FACTORS.keys(),None):
            raise ValueError('Invalid ingredient unit')
        if ing.get('quantity') is not None and float(ing['quantity']) <= 0:
            raise ValueError('Ingredient quantity must be positive')
        ing['optional'] = bool(ing.get('optional',False))
    result['servings'] = int(result.get('servings') or servings)
    if not 1 <= result['servings'] <= 30:
        raise ValueError('Invalid servings')
    for field in ('prep_minutes','cook_minutes'):
        if result.get(field) is not None:
            result[field] = int(result[field])
            if not 0 <= result[field] <= 1440:
                raise ValueError('Invalid duration')
    result['cuisine'] = result.get('cuisine') or 'Mauritian-inspired'
    return result
