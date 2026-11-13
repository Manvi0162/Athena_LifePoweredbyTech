-- LiveBetter schema repair and receipt confirmation
-- Designed for the existing schema. Does not drop tables or records.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS public.extracted_documents (
 id bigint generated always as identity primary key,
 source_filename text not null,
 image_sha256 text not null unique,
 document_type text,
 raw_text text not null,
 fields jsonb not null default '[]'::jsonb,
 uncertain_parts jsonb not null default '[]'::jsonb,
 review_status text default 'pending_review',
 created_at timestamptz default now()
);
CREATE TABLE IF NOT EXISTS public.households (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id),
 name text not null default 'My Household',
 members integer not null default 1 check (members > 0),
 currency text not null default 'MUR',
 preferences jsonb not null default '{}'::jsonb,
 budget_goals jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now()
);
CREATE TABLE IF NOT EXISTS public.utility_bills (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 kind text not null check (kind in ('water','electricity')),
 period_start date not null,
 period_end date not null,
 units numeric(12,3) not null check (units >= 0),
 amount numeric(12,2) not null check (amount >= 0),
 tariff_code text,
 created_at timestamptz not null default now(),
 check (period_end >= period_start)
);
CREATE TABLE IF NOT EXISTS public.meter_readings (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 kind text not null check (kind in ('water','electricity')),
 reading numeric(14,3) not null check (reading >= 0),
 captured_at timestamptz not null default now()
);
CREATE TABLE IF NOT EXISTS public.grocery_receipts (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 source_identifier text not null,
 retailer text,
 receipt_date date,
 total numeric(12,2) check (total >= 0),
 currency text not null default 'MUR',
 created_at timestamptz not null default now(),
 unique (household_id, source_identifier),
 unique (id, household_id)
);
CREATE TABLE IF NOT EXISTS public.receipt_items (
 id uuid primary key default gen_random_uuid(),
 receipt_id uuid not null references public.grocery_receipts(id),
 original_name text not null,
 normalized_name text not null,
 quantity numeric(12,3) not null check (quantity > 0),
 unit text not null,
 line_total numeric(12,2) check (line_total >= 0),
 created_at timestamptz not null default now()
);
CREATE TABLE IF NOT EXISTS public.pantry_items (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 ingredient_name text not null,
 quantity numeric(12,3) not null default 0 check (quantity >= 0),
 unit text not null,
 expiry_date date,
 available boolean not null default true,
 updated_at timestamptz not null default now(),
 unique (household_id, ingredient_name, unit),
 unique (id, household_id)
);
CREATE TABLE IF NOT EXISTS public.pantry_events (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 pantry_item_id uuid not null,
 quantity_delta numeric(12,3) not null,
 reason text not null,
 operation_id uuid,
 created_at timestamptz not null default now(),
 foreign key (pantry_item_id, household_id)
   references public.pantry_items(id, household_id)
);
CREATE TABLE IF NOT EXISTS public.household_actions (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 action_type text not null,
 assumptions jsonb not null default '{}'::jsonb,
 status text not null default 'selected',
 created_at timestamptz not null default now()
);
CREATE TABLE IF NOT EXISTS public.activity_logs (
 id uuid primary key default gen_random_uuid(),
 household_id uuid not null references public.households(id),
 event_type text not null,
 related_entity_id uuid,
 details jsonb not null default '{}'::jsonb,
 created_at timestamptz not null default now()
);
CREATE TABLE IF NOT EXISTS public.cooking_operations (
 id uuid primary key,
 household_id uuid not null references public.households(id),
 recipe_id text not null,
 created_at timestamptz not null default now()
);

-- Idempotent policy replacement, avoiding duplicate-policy errors.
DO $$
DECLARE
 t text;
 policy_name text;
BEGIN
 FOREACH t IN ARRAY ARRAY[
  'households','utility_bills','meter_readings','grocery_receipts',
  'receipt_items','pantry_items','pantry_events','household_actions',
  'activity_logs','cooking_operations'
 ] LOOP
  EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  policy_name := CASE t
    WHEN 'households' THEN 'Owners access households'
    WHEN 'utility_bills' THEN 'Owners access utility bills'
    WHEN 'meter_readings' THEN 'Owners access meter readings'
    WHEN 'grocery_receipts' THEN 'Owners access grocery receipts'
    WHEN 'receipt_items' THEN 'Owners access receipt items'
    WHEN 'pantry_items' THEN 'Owners access pantry items'
    WHEN 'pantry_events' THEN 'Owners access pantry events'
    WHEN 'household_actions' THEN 'Owners access household actions'
    WHEN 'activity_logs' THEN 'Owners access activity logs'
    WHEN 'cooking_operations' THEN 'Owners access cooking operations'
  END;
  EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', policy_name, t);
  IF t = 'households' THEN
   EXECUTE format('CREATE POLICY %I ON public.%I FOR ALL TO authenticated USING (owner_id = (select auth.uid())) WITH CHECK (owner_id = (select auth.uid()))', policy_name, t);
  ELSIF t = 'receipt_items' THEN
   EXECUTE format($p$CREATE POLICY %I ON public.%I FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.grocery_receipts r JOIN public.households h ON h.id = r.household_id WHERE r.id = receipt_id AND h.owner_id = (select auth.uid())))
    WITH CHECK (EXISTS (SELECT 1 FROM public.grocery_receipts r JOIN public.households h ON h.id = r.household_id WHERE r.id = receipt_id AND h.owner_id = (select auth.uid())))$p$, policy_name, t);
  ELSE
   EXECUTE format($p$CREATE POLICY %I ON public.%I FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM public.households h WHERE h.id = household_id AND h.owner_id = (select auth.uid())))
    WITH CHECK (EXISTS (SELECT 1 FROM public.households h WHERE h.id = household_id AND h.owner_id = (select auth.uid())))$p$, policy_name, t);
  END IF;
 END LOOP;
END $$;

-- OCR proposals are sensitive: disable public access until a household-linked
-- owner policy is designed. Server-side privileged code may access them.
ALTER TABLE public.extracted_documents ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.extracted_documents FROM anon, authenticated;

-- Atomic, authenticated, idempotent receipt confirmation.
CREATE OR REPLACE FUNCTION public.confirm_grocery_receipt(
 p_household_id uuid,
 p_source_identifier text,
 p_retailer text,
 p_receipt_date date,
 p_total numeric,
 p_items jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
 v_receipt_id uuid;
 v_item jsonb;
 v_name text;
 v_unit text;
 v_original text;
 v_quantity numeric;
 v_price numeric;
 v_pantry_id uuid;
BEGIN
 IF (SELECT auth.uid()) IS NULL OR NOT EXISTS (
  SELECT 1 FROM public.households h
  WHERE h.id = p_household_id AND h.owner_id = (SELECT auth.uid())
 ) THEN
  RAISE EXCEPTION 'Unauthorized household' USING ERRCODE = '42501';
 END IF;

 IF p_source_identifier IS NULL OR btrim(p_source_identifier) = ''
    OR p_total IS NULL OR p_total < 0
    OR p_items IS NULL OR jsonb_typeof(p_items) IS DISTINCT FROM 'array'
    OR jsonb_array_length(p_items) = 0 THEN
  RAISE EXCEPTION 'Invalid receipt input' USING ERRCODE = '22023';
 END IF;

 -- First insert wins. A repeated identifier returns the existing receipt
 -- without touching inventory or ledger entries.
 INSERT INTO public.grocery_receipts (
  household_id, source_identifier, retailer, receipt_date, total
 ) VALUES (
  p_household_id, p_source_identifier, p_retailer, p_receipt_date, p_total
 ) ON CONFLICT (household_id, source_identifier) DO NOTHING
 RETURNING id INTO v_receipt_id;

 IF v_receipt_id IS NULL THEN
  SELECT r.id INTO v_receipt_id
  FROM public.grocery_receipts r
  WHERE r.household_id = p_household_id
    AND r.source_identifier = p_source_identifier;
  IF v_receipt_id IS NULL THEN
   RAISE EXCEPTION 'Could not resolve duplicate receipt';
  END IF;
  RETURN v_receipt_id;
 END IF;

 FOR v_item IN SELECT value FROM jsonb_array_elements(p_items) LOOP
  IF jsonb_typeof(v_item) <> 'object' THEN
   RAISE EXCEPTION 'Each item must be a JSON object' USING ERRCODE = '22023';
  END IF;
  v_name := lower(btrim(v_item->>'normalized_name'));
  v_unit := lower(btrim(v_item->>'unit'));
  v_original := nullif(btrim(v_item->>'original_name'), '');

  IF coalesce(v_name,'') = '' OR coalesce(v_unit,'') = ''
     OR v_unit NOT IN ('kg','g','l','ml','piece')
     OR (v_item->>'quantity') IS NULL
     OR (v_item->>'quantity') !~ '^[0-9]+(\.[0-9]+)?$'
     OR ((v_item->>'line_total') IS NOT NULL AND (v_item->>'line_total') !~ '^[0-9]+(\.[0-9]+)?$') THEN
   RAISE EXCEPTION 'Invalid item name, unit, quantity or price' USING ERRCODE = '22023';
  END IF;
  v_quantity := (v_item->>'quantity')::numeric;
  v_price := (v_item->>'line_total')::numeric;
  IF v_quantity <= 0 OR v_quantity > 999999999 THEN
   RAISE EXCEPTION 'Item quantity out of range' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.receipt_items (
   receipt_id, original_name, normalized_name, quantity, unit, line_total
  ) VALUES (
   v_receipt_id, coalesce(v_original,v_name), v_name, v_quantity, v_unit, v_price
  );

  INSERT INTO public.pantry_items (
   household_id, ingredient_name, quantity, unit
  ) VALUES (
   p_household_id, v_name, v_quantity, v_unit
  ) ON CONFLICT (household_id, ingredient_name, unit)
  DO UPDATE SET
   quantity = public.pantry_items.quantity + EXCLUDED.quantity,
   available = true,
   updated_at = now()
  RETURNING id INTO v_pantry_id;

  INSERT INTO public.pantry_events (
   household_id, pantry_item_id, quantity_delta, reason
  ) VALUES (
   p_household_id, v_pantry_id, v_quantity, 'receipt_purchase'
  );
 END LOOP;

 INSERT INTO public.activity_logs (household_id,event_type,related_entity_id)
 VALUES (p_household_id,'receipt_confirmed',v_receipt_id);
 RETURN v_receipt_id;
END;
$$;

REVOKE ALL ON FUNCTION public.confirm_grocery_receipt(uuid,text,text,date,numeric,jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.confirm_grocery_receipt(uuid,text,text,date,numeric,jsonb) TO authenticated;
COMMIT;
NOTIFY pgrst, 'reload schema';

-- Verification: should return one row with the six named arguments.
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS parameters
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname = 'confirm_grocery_receipt';

-- =============================================================
-- LiveBetter: unified recipe catalogue (Colab-compatible)
-- Existing legacy recipes tables, if present, are not deleted.
-- =============================================================
BEGIN;

CREATE TABLE IF NOT EXISTS public.lb_recipes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid REFERENCES public.households(id) ON DELETE CASCADE,
    name text NOT NULL,
    cuisine text NOT NULL DEFAULT 'Mauritian',
    description text,
    servings integer NOT NULL DEFAULT 4 CHECK (servings > 0),
    source_type text NOT NULL DEFAULT 'curated',
    verification_status text NOT NULL DEFAULT 'pending',
    source_url text,
    youtube_url text,
    prep_minutes integer CHECK (prep_minutes IS NULL OR prep_minutes >= 0),
    cook_minutes integer CHECK (cook_minutes IS NULL OR cook_minutes >= 0),
    instructions jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT lb_recipes_source_type_check CHECK (source_type IN ('curated','ai_generated','imported')),
    CONSTRAINT lb_recipes_verification_check CHECK (verification_status IN ('pending','verified','rejected')),
    CONSTRAINT lb_recipes_instructions_array_check CHECK (jsonb_typeof(instructions) = 'array')
);

CREATE TABLE IF NOT EXISTS public.lb_recipe_ingredients (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id uuid NOT NULL REFERENCES public.lb_recipes(id) ON DELETE CASCADE,
    ingredient_name text NOT NULL,
    quantity numeric(12,3) CHECK (quantity IS NULL OR quantity > 0),
    unit text,
    optional boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_lb_recipes_household
    ON public.lb_recipes (household_id);
CREATE INDEX IF NOT EXISTS idx_lb_recipes_status
    ON public.lb_recipes (verification_status);
CREATE INDEX IF NOT EXISTS idx_lb_recipe_ingredients_recipe
    ON public.lb_recipe_ingredients (recipe_id);
CREATE INDEX IF NOT EXISTS idx_lb_recipe_ingredients_name
    ON public.lb_recipe_ingredients (lower(ingredient_name));

ALTER TABLE public.lb_recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lb_recipe_ingredients ENABLE ROW LEVEL SECURITY;

-- A verified shared recipe is readable by any signed-in user.
-- A private recipe is readable only by its household owner.
DROP POLICY IF EXISTS "Read verified recipes" ON public.lb_recipes;
DROP POLICY IF EXISTS "lb_read_recipes" ON public.lb_recipes;
CREATE POLICY "lb_read_recipes" ON public.lb_recipes
FOR SELECT TO authenticated
USING (
    (household_id IS NULL AND verification_status = 'verified')
    OR EXISTS (
        SELECT 1 FROM public.households h
        WHERE h.id = lb_recipes.household_id
          AND h.owner_id = (SELECT auth.uid())
    )
);

-- Household owners may save AI suggestions as pending private recipes.
DROP POLICY IF EXISTS "lb_insert_private_recipes" ON public.lb_recipes;
CREATE POLICY "lb_insert_private_recipes" ON public.lb_recipes
FOR INSERT TO authenticated
WITH CHECK (
    household_id IS NOT NULL
    AND source_type = 'ai_generated'
    AND verification_status = 'pending'
    AND EXISTS (
        SELECT 1 FROM public.households h
        WHERE h.id = lb_recipes.household_id
          AND h.owner_id = (SELECT auth.uid())
    )
);

DROP POLICY IF EXISTS "Read verified recipe ingredients" ON public.lb_recipe_ingredients;
DROP POLICY IF EXISTS "lb_read_recipe_ingredients" ON public.lb_recipe_ingredients;
CREATE POLICY "lb_read_recipe_ingredients" ON public.lb_recipe_ingredients
FOR SELECT TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.lb_recipes r
        WHERE r.id = lb_recipe_ingredients.recipe_id
          AND (
              (r.household_id IS NULL AND r.verification_status = 'verified')
              OR EXISTS (
                  SELECT 1 FROM public.households h
                  WHERE h.id = r.household_id
                    AND h.owner_id = (SELECT auth.uid())
              )
          )
    )
);

DROP POLICY IF EXISTS "lb_insert_private_recipe_ingredients" ON public.lb_recipe_ingredients;
CREATE POLICY "lb_insert_private_recipe_ingredients" ON public.lb_recipe_ingredients
FOR INSERT TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.lb_recipes r
        JOIN public.households h ON h.id = r.household_id
        WHERE r.id = lb_recipe_ingredients.recipe_id
          AND h.owner_id = (SELECT auth.uid())
          AND r.source_type = 'ai_generated'
          AND r.verification_status = 'pending'
    )
);

COMMIT;
NOTIFY pgrst, 'reload schema';

-- Check that both tables exist.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('lb_recipes', 'lb_recipe_ingredients')
ORDER BY table_name;


CREATE OR REPLACE FUNCTION public.lb_save_ai_recipe(
    p_household_id uuid,
    p_recipe jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_recipe_id uuid;
    v_name text;
    v_ingredients jsonb;
    v_instructions jsonb;
    v_item jsonb;
    v_quantity numeric;
BEGIN
    -- Require an authenticated household owner
    IF (SELECT auth.uid()) IS NULL
       OR NOT EXISTS (
           SELECT 1
           FROM public.households h
           WHERE h.id = p_household_id
             AND h.owner_id = (SELECT auth.uid())
       )
    THEN
        RAISE EXCEPTION 'Unauthorized household'
            USING ERRCODE = '42501';
    END IF;

    IF p_recipe IS NULL
       OR jsonb_typeof(p_recipe) <> 'object'
    THEN
        RAISE EXCEPTION 'Recipe must be a JSON object';
    END IF;

    v_name := NULLIF(
        btrim(COALESCE(
            p_recipe->>'name',
            p_recipe->>'recipe_name'
        )),
        ''
    );

    v_ingredients := p_recipe->'ingredients';

    v_instructions := COALESCE(
        p_recipe->'instructions',
        '[]'::jsonb
    );

    IF v_name IS NULL THEN
        RAISE EXCEPTION 'Recipe name is required';
    END IF;

    IF jsonb_typeof(v_ingredients) IS DISTINCT FROM 'array'
       OR jsonb_array_length(v_ingredients) = 0
    THEN
        RAISE EXCEPTION 'Recipe ingredients must be a non-empty array';
    END IF;

    IF jsonb_typeof(v_instructions) IS DISTINCT FROM 'array'
    THEN
        RAISE EXCEPTION 'Instructions must be an array';
    END IF;

    -- Insert private pending recipe
    INSERT INTO public.lb_recipes (
        household_id,
        name,
        cuisine,
        description,
        servings,
        source_type,
        verification_status,
        source_url,
        youtube_url,
        prep_minutes,
        cook_minutes,
        instructions
    )
    VALUES (
        p_household_id,
        v_name,
        COALESCE(
            NULLIF(btrim(p_recipe->>'cuisine'), ''),
            'Mauritian'
        ),
        p_recipe->>'description',
        GREATEST(
            1,
            COALESCE(
                NULLIF(p_recipe->>'servings', '')::integer,
                4
            )
        ),
        'ai_generated',
        'pending',
        NULL,
        NULL,
        NULLIF(p_recipe->>'prep_minutes', '')::integer,
        NULLIF(p_recipe->>'cook_minutes', '')::integer,
        v_instructions
    )
    RETURNING id INTO v_recipe_id;

    -- Insert recipe ingredients
    FOR v_item IN
        SELECT value
        FROM jsonb_array_elements(v_ingredients)
    LOOP
        IF jsonb_typeof(v_item) <> 'object' THEN
            RAISE EXCEPTION 'Each ingredient must be an object';
        END IF;

        IF NULLIF(btrim(COALESCE(
            v_item->>'ingredient_name',
            v_item->>'name'
        )), '') IS NULL THEN
            RAISE EXCEPTION 'Ingredient name is required';
        END IF;

        v_quantity := NULLIF(
            v_item->>'quantity', ''
        )::numeric;

        IF v_quantity IS NOT NULL AND v_quantity <= 0 THEN
            RAISE EXCEPTION 'Ingredient quantity must be positive';
        END IF;

        INSERT INTO public.lb_recipe_ingredients (
            recipe_id,
            ingredient_name,
            quantity,
            unit,
            optional
        )
        VALUES (
            v_recipe_id,
            COALESCE(
                NULLIF(btrim(v_item->>'ingredient_name'), ''),
                NULLIF(btrim(v_item->>'name'), '')
            ),
            v_quantity,
            v_item->>'unit',
            COALESCE(
                NULLIF(v_item->>'optional', '')::boolean,
                false
            )
        );
    END LOOP;

    RETURN v_recipe_id;
END;
$$;

-- Only authenticated users can call the function
REVOKE ALL ON FUNCTION
public.lb_save_ai_recipe(uuid, jsonb)
FROM PUBLIC, anon;

GRANT EXECUTE ON FUNCTION
public.lb_save_ai_recipe(uuid, jsonb)
TO authenticated;

-- Refresh Supabase API schema
NOTIFY pgrst, 'reload schema';


SELECT
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name = 'lb_save_ai_recipe';




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
    v_pantry_id uuid;
    v_updated_count integer;
    v_existing_recipe text;
    v_count integer := 0;
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
    INSERT INTO public.cooking_operations (
        id, household_id, recipe_id
    )
    VALUES (
        p_operation_id,
        p_household_id,
        p_recipe_id::text
    )
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

    -- Deduct required ingredients only
    -- Aggregate duplicates before updating stock
    FOR v_ingredient IN
        SELECT
            lower(btrim(ingredient_name)) AS name,
            lower(btrim(unit)) AS unit,
            SUM(quantity) AS required_quantity
        FROM public.lb_recipe_ingredients
        WHERE recipe_id = p_recipe_id
          AND optional = false
        GROUP BY
            lower(btrim(ingredient_name)),
            lower(btrim(unit))
        ORDER BY 1, 2
    LOOP
        IF v_ingredient.required_quantity IS NULL
           OR v_ingredient.required_quantity <= 0
           OR v_ingredient.unit IS NULL THEN
            RAISE EXCEPTION
                'Invalid quantity or unit for ingredient %',
                v_ingredient.name;
        END IF;

        -- Atomic deduction prevents negative stock
        UPDATE public.pantry_items
        SET
            quantity = quantity
                - v_ingredient.required_quantity,
            available = (
                quantity - v_ingredient.required_quantity > 0
            ),
            updated_at = now()
        WHERE household_id = p_household_id
          AND lower(btrim(ingredient_name)) =
              v_ingredient.name
          AND lower(btrim(unit)) =
              v_ingredient.unit
          AND quantity >= v_ingredient.required_quantity
        RETURNING id INTO v_pantry_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION
                'Missing or insufficient ingredient: % (%)',
                v_ingredient.name,
                v_ingredient.unit;
        END IF;

        INSERT INTO public.pantry_events (
            household_id,
            pantry_item_id,
            quantity_delta,
            reason,
            operation_id
        )
        VALUES (
            p_household_id,
            v_pantry_id,
            -v_ingredient.required_quantity,
            'recipe_cooked',
            p_operation_id
        );

        v_count := v_count + 1;
    END LOOP;

    INSERT INTO public.activity_logs (
        household_id,
        event_type,
        related_entity_id,
        details
    )
    VALUES (
        p_household_id,
        'recipe_cooked',
        p_recipe_id,
        jsonb_build_object(
            'operation_id', p_operation_id,
            'ingredients_deducted', v_count
        )
    );

    RETURN jsonb_build_object(
        'status', 'confirmed',
        'operation_id', p_operation_id,
        'ingredients_deducted', v_count
    );
END;
$$;

REVOKE ALL ON FUNCTION
public.lb_confirm_cooking(uuid, uuid, uuid)
FROM PUBLIC, anon;

GRANT EXECUTE ON FUNCTION
public.lb_confirm_cooking(uuid, uuid, uuid)
TO authenticated;

NOTIFY pgrst, 'reload schema';