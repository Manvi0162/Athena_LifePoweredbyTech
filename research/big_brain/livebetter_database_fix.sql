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
