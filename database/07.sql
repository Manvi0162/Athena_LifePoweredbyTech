-- 07: ADD CORN KERNELS AND FIVE MAURITIAN-INSPIRED DEMO RECIPES
-- Run AFTER 06_livebetter_full_demo_seed.sql on the SAME Supabase project.
-- Only modifies the dedicated demo household "LiveBetter Full Demo - Seed 06".
-- Safe to rerun: uses stable recipe/ingredient IDs and tops corn stock to 500 g.
-- These are manually authored TEST FIXTURES, not imported UniTools recipes.
-- They are intentionally marked verified for household-private demo matching ONLY.
-- Do not mistake them for externally verified dataset recipes.
-- Existing stock, other households and grocery spending are not overwritten.

BEGIN;
DO $seed$
DECLARE
    v_email text := 'demo@livebetter.test'; -- CHANGE ME
    v_h uuid;
    v_pantry_id uuid;
    v_have numeric;
    v_delta numeric;
    v_r jsonb;
    v_i record;
    v_recipe_id uuid;
    v_ingredient_id uuid;
    v_recipes jsonb := $recipes$
[
  {
    "slug": "corn_vegetable_fried_rice",
    "name": "Mauritian-inspired Corn Vegetable Fried Rice (DEMO)",
    "cuisine": "Mauritian-inspired",
    "description": "Fictional demo fixture for database-first recipe matching; not sourced from the UniTools dataset.",
    "servings": 4,
    "prep_minutes": 15,
    "cook_minutes": 15,
    "ingredients": [
      [
        "rice",
        400,
        "g"
      ],
      [
        "corn kernels",
        150,
        "g"
      ],
      [
        "carrot",
        150,
        "g"
      ],
      [
        "peas",
        100,
        "g"
      ],
      [
        "onion",
        100,
        "g"
      ],
      [
        "egg",
        2,
        "piece"
      ],
      [
        "cooking oil",
        20,
        "ml"
      ]
    ],
    "instructions": [
      "Cook the rice and cool it safely.",
      "Chop the onion and carrot; drain corn kernels.",
      "Cook vegetables, peas and corn in a little oil.",
      "Scramble eggs until fully cooked; stir in rice and serve hot."
    ]
  },
  {
    "slug": "corn_vegetable_mine_frite",
    "name": "Mauritian-inspired Corn Vegetable Mine Frite (DEMO)",
    "cuisine": "Mauritian-inspired",
    "description": "Fictional demo fixture; not a historically verified traditional recipe.",
    "servings": 4,
    "prep_minutes": 15,
    "cook_minutes": 15,
    "ingredients": [
      [
        "noodles",
        400,
        "g"
      ],
      [
        "corn kernels",
        150,
        "g"
      ],
      [
        "cabbage",
        200,
        "g"
      ],
      [
        "carrot",
        100,
        "g"
      ],
      [
        "onion",
        100,
        "g"
      ],
      [
        "cooking oil",
        25,
        "ml"
      ]
    ],
    "instructions": [
      "Cook noodles according to packaging and drain.",
      "Slice cabbage, carrot and onion.",
      "Stir-fry vegetables and drained corn until cooked.",
      "Add noodles and toss thoroughly before serving."
    ]
  },
  {
    "slug": "sweetcorn_soup",
    "name": "Mauritian-inspired Sweetcorn Soup (DEMO)",
    "cuisine": "Mauritian-inspired",
    "description": "Simple original demo soup using corn kernels; pantry water is assumed and untracked.",
    "servings": 4,
    "prep_minutes": 10,
    "cook_minutes": 20,
    "ingredients": [
      [
        "corn kernels",
        250,
        "g"
      ],
      [
        "onion",
        100,
        "g"
      ],
      [
        "garlic",
        10,
        "g"
      ],
      [
        "carrot",
        100,
        "g"
      ],
      [
        "cooking oil",
        10,
        "ml"
      ]
    ],
    "instructions": [
      "Drain and rinse corn if canned.",
      "Finely chop onion, garlic and carrot.",
      "Soften vegetables in oil, then add water and simmer until tender.",
      "Blend part of the soup for creaminess, heat through and serve."
    ]
  },
  {
    "slug": "corn_fritters",
    "name": "Mauritian-inspired Sweetcorn Fritters (DEMO)",
    "cuisine": "Mauritian-inspired",
    "description": "Original demo recipe for a simple corn fritter; oil quantities are illustrative.",
    "servings": 4,
    "prep_minutes": 15,
    "cook_minutes": 15,
    "ingredients": [
      [
        "corn kernels",
        200,
        "g"
      ],
      [
        "flour",
        150,
        "g"
      ],
      [
        "egg",
        2,
        "piece"
      ],
      [
        "onion",
        80,
        "g"
      ],
      [
        "cooking oil",
        40,
        "ml"
      ]
    ],
    "instructions": [
      "Drain corn thoroughly and finely chop onion.",
      "Mix flour and egg, adding a little water to make a thick batter.",
      "Fold in corn and onion.",
      "Pan-fry small portions until golden and fully cooked; serve hot."
    ]
  },
  {
    "slug": "corn_potato_curry",
    "name": "Mauritian-inspired Corn and Potato Curry (DEMO)",
    "cuisine": "Mauritian-inspired",
    "description": "Fictional demo corn and potato curry; quantities are illustrative.",
    "servings": 4,
    "prep_minutes": 15,
    "cook_minutes": 25,
    "ingredients": [
      [
        "corn kernels",
        200,
        "g"
      ],
      [
        "potato",
        500,
        "g"
      ],
      [
        "tomato",
        200,
        "g"
      ],
      [
        "onion",
        120,
        "g"
      ],
      [
        "garlic",
        10,
        "g"
      ],
      [
        "cooking oil",
        20,
        "ml"
      ]
    ],
    "instructions": [
      "Peel and cube the potatoes; dice tomato, onion and garlic.",
      "Soften onion and garlic in oil, then add potato and tomato.",
      "Add enough water and cook until potatoes are tender.",
      "Add corn kernels, simmer until heated through, season to taste and serve."
    ]
  }
]
$recipes$::jsonb;
BEGIN
    SELECT h.id INTO v_h
    FROM public.households h
    JOIN auth.users u ON h.owner_id = u.id
    WHERE lower(u.email) = lower(v_email)
      AND h.name = 'LiveBetter Full Demo - Seed 06'
    LIMIT 1;

    IF v_h IS NULL THEN
        RAISE EXCEPTION 'Seed 06 demo household not found for email %. Run 06 first or check your account email.', v_email;
    END IF;

    -- Add 500 grams of corn kernels, or top up existing stock to 500 grams.
    -- Stock is a demo/manual adjustment, not a fictional receipt purchase.
    SELECT id, quantity INTO v_pantry_id, v_have
    FROM public.pantry_items
    WHERE household_id = v_h
      AND ingredient_name = 'corn kernels'
      AND unit = 'g'
    FOR UPDATE;

    IF v_pantry_id IS NULL THEN
        INSERT INTO public.pantry_items
            (household_id, ingredient_name, quantity, unit, available)
        VALUES (v_h, 'corn kernels', 500, 'g', true)
        RETURNING id INTO v_pantry_id;
        v_delta := 500;
    ELSE
        v_delta := GREATEST(500 - v_have, 0);
        UPDATE public.pantry_items
        SET quantity = GREATEST(quantity, 500),
            available = true,
            updated_at = now()
        WHERE id = v_pantry_id;
    END IF;

    IF v_delta > 0 THEN
        INSERT INTO public.pantry_events
            (household_id, pantry_item_id, quantity_delta, reason)
        VALUES (v_h, v_pantry_id, v_delta, 'demo_manual_stock_adjustment');
    END IF;

    -- Potato is required by the curry; add a separate 1 kg demo stock entry.
    SELECT id, quantity INTO v_pantry_id, v_have
    FROM public.pantry_items
    WHERE household_id = v_h
      AND ingredient_name = 'potato'
      AND unit = 'g'
    FOR UPDATE;

    IF v_pantry_id IS NULL THEN
        INSERT INTO public.pantry_items
            (household_id, ingredient_name, quantity, unit, available)
        VALUES (v_h, 'potato', 1000, 'g', true)
        RETURNING id INTO v_pantry_id;
        v_delta := 1000;
    ELSE
        v_delta := GREATEST(1000 - v_have, 0);
        UPDATE public.pantry_items
        SET quantity = GREATEST(quantity, 1000),
            available = true,
            updated_at = now()
        WHERE id = v_pantry_id;
    END IF;
    IF v_delta > 0 THEN
        INSERT INTO public.pantry_events
            (household_id, pantry_item_id, quantity_delta, reason)
        VALUES (v_h, v_pantry_id, v_delta, 'demo_manual_stock_adjustment');
    END IF;

    -- Stable IDs match the same approach used by seed 06.
    FOR v_r IN SELECT value FROM jsonb_array_elements(v_recipes) LOOP
        v_recipe_id := md5(v_h::text || ':recipe:' || (v_r->>'slug'))::uuid;
        INSERT INTO public.lb_recipes
            (id, household_id, name, cuisine, description, servings,
             source_type, verification_status, source_url, youtube_url,
             prep_minutes, cook_minutes, instructions)
        VALUES (
            v_recipe_id, v_h, v_r->>'name', v_r->>'cuisine',
            v_r->>'description', (v_r->>'servings')::integer,
            'curated', 'verified', NULL, NULL,
            (v_r->>'prep_minutes')::integer,
            (v_r->>'cook_minutes')::integer, v_r->'instructions'
        ) ON CONFLICT (id) DO NOTHING;

        FOR v_i IN
            SELECT value AS ingredient, ordinality AS n
            FROM jsonb_array_elements(v_r->'ingredients') WITH ORDINALITY
        LOOP
            v_ingredient_id := md5(v_recipe_id::text || ':ingredient:' || v_i.n::text)::uuid;
            INSERT INTO public.lb_recipe_ingredients
                (id, recipe_id, ingredient_name, quantity, unit, optional)
            VALUES (
                v_ingredient_id, v_recipe_id,
                v_i.ingredient->>0,
                (v_i.ingredient->>1)::numeric,
                v_i.ingredient->>2,
                false
            ) ON CONFLICT (id) DO NOTHING;
        END LOOP;
    END LOOP;

    RAISE NOTICE 'Added corn & potato demo stock and five corn recipe fixtures for household %', v_h;
END
$seed$;
COMMIT;

-- VERIFICATION: see all corn recipes and whether demo pantry can cook them NOW.
WITH demo AS (
    SELECT h.id
    FROM public.households h JOIN auth.users u ON u.id = h.owner_id
    WHERE lower(u.email) = lower('demo@livebetter.test') -- CHANGE ME
      AND h.name = 'LiveBetter Full Demo - Seed 06'
), matches AS (
    SELECT r.id, r.name,
           count(*) FILTER (WHERE i.optional = false) AS needed,
           count(*) FILTER (WHERE i.optional = false AND
             coalesce(p.quantity, 0) >= i.quantity AND p.available = true) AS available
    FROM public.lb_recipes r
    JOIN public.lb_recipe_ingredients i ON i.recipe_id = r.id
    LEFT JOIN public.pantry_items p
      ON p.household_id = r.household_id
     AND p.ingredient_name = lower(trim(i.ingredient_name))
     AND p.unit = i.unit
    WHERE r.household_id IN (SELECT id FROM demo)
      AND r.name ILIKE '%corn%'
    GROUP BY r.id, r.name
)
SELECT name, needed AS required_ingredients, available AS sufficient_ingredients,
       (needed = available) AS cookable_now
FROM matches ORDER BY name;
