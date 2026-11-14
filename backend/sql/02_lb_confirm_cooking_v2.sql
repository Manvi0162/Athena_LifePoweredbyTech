-- LiveBetter: lb_confirm_cooking v2
-- Replaces the existing function (same name, arguments and return type).
-- Unchanged: ownership check, recipe access check, one deduction per
-- operation_id, atomic all-or-nothing, no negative stock.
-- Changed:
--   1. Water is never deducted (not tracked in the pantry).
--   2. A required ingredient that is not in the pantry is skipped and
--      reported, instead of blocking the whole cook.
--   3. kg<->g and l<->ml are converted to the pantry's unit.
-- A tracked ingredient with too little stock still fails the whole cook.

CREATE OR REPLACE FUNCTION public.lb_confirm_cooking(
    p_household_id uuid,
    p_recipe_id uuid,
    p_operation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_ingredient record;
    v_pantry record;
    v_updated_count integer;
    v_existing_recipe text;
    v_count integer := 0;
    v_need numeric;
    v_deducted jsonb := '[]'::jsonb;
    v_skipped jsonb := '[]'::jsonb;
BEGIN
    -- Verify household ownership
    IF NOT EXISTS (
        SELECT 1
        FROM public.households h
        WHERE h.id = p_household_id
          AND h.owner_id = (SELECT auth.uid())
    ) THEN
        RAISE EXCEPTION 'Unauthorized household';
    END IF;

    -- Only verified or own household recipes
    IF NOT EXISTS (
        SELECT 1
        FROM public.lb_recipes r
        WHERE r.id = p_recipe_id
          AND (
              r.verification_status = 'verified'
              OR r.household_id = p_household_id
          )
    ) THEN
        RAISE EXCEPTION 'Recipe not accessible';
    END IF;

    -- Reject duplicate cooking operations
    INSERT INTO public.cooking_operations (id, household_id, recipe_id)
    VALUES (p_operation_id, p_household_id, p_recipe_id::text)
    ON CONFLICT (id) DO NOTHING;

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    IF v_updated_count = 0 THEN
        SELECT recipe_id
        INTO v_existing_recipe
        FROM public.cooking_operations
        WHERE id = p_operation_id
          AND household_id = p_household_id;

        IF v_existing_recipe IS DISTINCT FROM p_recipe_id::text THEN
            RAISE EXCEPTION 'Operation ID already used';
        END IF;

        RETURN jsonb_build_object(
            'status', 'already_confirmed',
            'operation_id', p_operation_id
        );
    END IF;

    -- Require at least one mandatory ingredient
    IF NOT EXISTS (
        SELECT 1
        FROM public.lb_recipe_ingredients
        WHERE recipe_id = p_recipe_id
          AND optional = false
    ) THEN
        RAISE EXCEPTION 'Recipe has no required ingredients';
    END IF;

    -- Deduct required ingredients only; aggregate duplicates first
    FOR v_ingredient IN
        SELECT
            lower(btrim(ingredient_name)) AS name,
            lower(btrim(unit)) AS unit,
            SUM(quantity) AS required_quantity
        FROM public.lb_recipe_ingredients
        WHERE recipe_id = p_recipe_id
          AND optional = false
        GROUP BY lower(btrim(ingredient_name)), lower(btrim(unit))
        ORDER BY 1, 2
    LOOP
        IF v_ingredient.required_quantity IS NULL
           OR v_ingredient.required_quantity <= 0
           OR v_ingredient.unit IS NULL THEN
            RAISE EXCEPTION 'Invalid quantity or unit for ingredient %',
                v_ingredient.name;
        END IF;

        -- 1. Water is not tracked in the pantry
        IF v_ingredient.name IN ('water', 'tap water', 'eau') THEN
            v_skipped := v_skipped || jsonb_build_object(
                'ingredient', v_ingredient.name,
                'reason', 'water is not tracked');
            CONTINUE;
        END IF;

        -- 3. Find stock in the same unit, or a convertible one.
        --    factor converts the recipe quantity into the pantry unit.
        SELECT p.id,
               p.quantity,
               p.unit AS pantry_unit,
               CASE
                   WHEN lower(btrim(p.unit)) = v_ingredient.unit THEN 1
                   WHEN v_ingredient.unit = 'kg' AND lower(btrim(p.unit)) = 'g' THEN 1000
                   WHEN v_ingredient.unit = 'g' AND lower(btrim(p.unit)) = 'kg' THEN 0.001
                   WHEN v_ingredient.unit = 'l' AND lower(btrim(p.unit)) = 'ml' THEN 1000
                   WHEN v_ingredient.unit = 'ml' AND lower(btrim(p.unit)) = 'l' THEN 0.001
               END::numeric AS factor
        INTO v_pantry
        FROM public.pantry_items p
        WHERE p.household_id = p_household_id
          AND lower(btrim(p.ingredient_name)) = v_ingredient.name
          AND (
              lower(btrim(p.unit)) = v_ingredient.unit
              OR (v_ingredient.unit IN ('kg', 'g') AND lower(btrim(p.unit)) IN ('kg', 'g'))
              OR (v_ingredient.unit IN ('l', 'ml') AND lower(btrim(p.unit)) IN ('l', 'ml'))
          )
        ORDER BY (lower(btrim(p.unit)) = v_ingredient.unit) DESC, p.quantity DESC
        LIMIT 1
        FOR UPDATE;

        -- 2. Not in the pantry: skip and report, do not block the cook
        IF NOT FOUND THEN
            v_skipped := v_skipped || jsonb_build_object(
                'ingredient', v_ingredient.name,
                'quantity', v_ingredient.required_quantity,
                'unit', v_ingredient.unit,
                'reason', 'not in pantry');
            CONTINUE;
        END IF;

        v_need := v_ingredient.required_quantity * v_pantry.factor;

        -- Tracked but too little stock: fail the whole cook (no negative stock)
        IF v_pantry.quantity < v_need THEN
            RAISE EXCEPTION 'Insufficient ingredient: % (need % %, have % %)',
                v_ingredient.name, round(v_need, 3), v_pantry.pantry_unit,
                v_pantry.quantity, v_pantry.pantry_unit;
        END IF;

        UPDATE public.pantry_items
        SET quantity = quantity - v_need,
            available = (quantity - v_need > 0),
            updated_at = now()
        WHERE id = v_pantry.id;

        INSERT INTO public.pantry_events (
            household_id, pantry_item_id, quantity_delta, reason, operation_id
        )
        VALUES (
            p_household_id, v_pantry.id, -v_need, 'recipe_cooked', p_operation_id
        );

        v_deducted := v_deducted || jsonb_build_object(
            'ingredient', v_ingredient.name,
            'quantity', v_need,
            'unit', v_pantry.pantry_unit);
        v_count := v_count + 1;
    END LOOP;

    INSERT INTO public.activity_logs (
        household_id, event_type, related_entity_id, details
    )
    VALUES (
        p_household_id,
        'recipe_cooked',
        p_recipe_id,
        jsonb_build_object(
            'operation_id', p_operation_id,
            'ingredients_deducted', v_count,
            'deducted', v_deducted,
            'skipped', v_skipped
        )
    );

    RETURN jsonb_build_object(
        'status', 'confirmed',
        'operation_id', p_operation_id,
        'ingredients_deducted', v_count,
        'deducted', v_deducted,
        'skipped', v_skipped
    );
END;
$$;

REVOKE ALL ON FUNCTION public.lb_confirm_cooking(uuid, uuid, uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.lb_confirm_cooking(uuid, uuid, uuid) TO authenticated;

NOTIFY pgrst, 'reload schema';
