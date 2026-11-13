-- LiveBetter / 05 - FICTIONAL DEMO DATA SEED
-- For Supabase SQL Editor, after migrations 01-04.
-- SAFETY: this creates/updates only a household named 'LiveBetter Demo Household - Seed 05'
-- owned by the Supabase Auth user whose email you supply below.
-- Re-running is designed not to duplicate purchases, bills, pantry or assessment records.
-- This creates synthetic demonstration data, NOT genuine measured bills or verified tariff forecasts.
-- Do not run against a project unless you intend to add fictional demo data.

BEGIN;
DO $seed$
DECLARE
  v_owner_email text := 'demo@livebetter.test'; -- <-- CHANGE THIS FIRST
  v_owner uuid;
  v_household uuid;
  v_receipt uuid;
  v_bill record;
  v_items jsonb := '[
    {"original_name":"RICE 2KG","normalized_name":"rice","quantity":2,"unit":"kg","line_total":120},
    {"original_name":"CARROTS 1KG","normalized_name":"carrots","quantity":1,"unit":"kg","line_total":65},
    {"original_name":"EGGS 6","normalized_name":"eggs","quantity":6,"unit":"piece","line_total":48}
  ]'::jsonb;
  v_item jsonb;
  v_pantry_id uuid;
BEGIN
  IF v_owner_email = 'REPLACE_WITH_YOUR_AUTH_EMAIL' THEN
    RAISE EXCEPTION 'Edit v_owner_email to your existing Supabase Auth account email before running.';
  END IF;

  SELECT id INTO v_owner FROM auth.users WHERE lower(email)=lower(v_owner_email) LIMIT 1;
  IF v_owner IS NULL THEN
    RAISE EXCEPTION 'Auth user % does not exist. Create the user via Supabase Authentication first.', v_owner_email;
  END IF;

  SELECT id INTO v_household FROM public.households
    WHERE owner_id=v_owner AND name='LiveBetter Demo Household - Seed 05'
    ORDER BY created_at LIMIT 1;

  IF v_household IS NULL THEN
    INSERT INTO public.households (owner_id, name, members, currency, preferences, budget_goals)
    VALUES (v_owner, 'LiveBetter Demo Household - Seed 05', 4, 'MUR',
      '{"diet":"none","allergies":[],"servings":4,"demo_data":true}'::jsonb,
      '{"groceries":12000,"electricity":2500,"water":500}'::jsonb)
    RETURNING id INTO v_household;
  END IF;

  INSERT INTO public.lb_user_preferences (user_id, preferred_language)
  VALUES (v_owner,'en') ON CONFLICT (user_id) DO NOTHING;

  INSERT INTO public.lb_household_modules (household_id,module,enabled,setup_status)
  VALUES (v_household,'food',true,'ready'),(v_household,'water',true,'ready'),
         (v_household,'electricity',true,'ready')
  ON CONFLICT (household_id,module) DO NOTHING;

  INSERT INTO public.lb_assessments (household_id,module,version,answers,completed)
  VALUES
    (v_household,'general',1,'{"household_members":4,"home_type":"house","occupancy":"most_of_day","main_goal":"all_of_the_above","demo_data":true}'::jsonb,true),
    (v_household,'water',1,'{"shower_duration":"5-10 min","flushes_per_person":"4-6","laundry_loads_per_week":"3-5","outdoor_water_use":"about_weekly","expected_change":"not_sure","demo_data":true}'::jsonb,true),
    (v_household,'electricity',1,'{"major_appliances":["air_conditioner","refrigerator","washing_machine"],"ac_hours_per_day":"1-3 h","water_heating":"electric","cooking_energy":"gas","expected_change":"no","demo_data":true}'::jsonb,true),
    (v_household,'food',1,'{"home_cooked_meals":"2","diet":"mixed","allergies":"unsure","grocery_frequency":"weekly","main_challenge":"food_expiring","demo_data":true}'::jsonb,true)
  ON CONFLICT (household_id,module,version) DO NOTHING;

  INSERT INTO public.lb_utility_profiles (household_id,kind,tariff_code,monthly_budget_mur,profile)
  VALUES
    (v_household,'water',NULL,500,'{"data_origin":"synthetic_demo","tariff_not_verified":true}'::jsonb),
    (v_household,'electricity',NULL,2500,'{"data_origin":"synthetic_demo","tariff_not_verified":true}'::jsonb)
  ON CONFLICT (household_id,kind) DO NOTHING;

  -- Fictional historical bills. Unique-by-check on household/kind/period is enforced here
  -- via NOT EXISTS because the base utility_bills table does not define a period unique index.
  FOR v_bill IN SELECT * FROM (VALUES
    ('water'::text, '2026-08-01'::date, '2026-08-31'::date, 17.0::numeric, 390.00::numeric),
    ('water', '2026-09-01'::date, '2026-09-30'::date, 18.0::numeric, 420.00::numeric),
    ('electricity', '2026-08-01'::date, '2026-08-31'::date, 245.0::numeric, 1650.00::numeric),
    ('electricity', '2026-09-01'::date, '2026-09-30'::date, 260.0::numeric, 1770.00::numeric)
  ) AS d(kind,period_start,period_end,units,amount)
  LOOP
    IF NOT EXISTS (
      SELECT 1 FROM public.utility_bills b
      WHERE b.household_id=v_household AND b.kind=v_bill.kind
        AND b.period_start=v_bill.period_start AND b.period_end=v_bill.period_end
    ) THEN
      INSERT INTO public.utility_bills
        (household_id,kind,period_start,period_end,units,amount,tariff_code,source_metadata)
      VALUES (v_household,v_bill.kind,v_bill.period_start,v_bill.period_end,
              v_bill.units,v_bill.amount,NULL,
              '{"origin":"fictional_demo_seed_05","verified_bill":false,"not_actual_usage":true}'::jsonb);
    END IF;
  END LOOP;

  -- Appliance power is a declared what-if ASSUMPTION, not measured wattage.
  IF NOT EXISTS (SELECT 1 FROM public.lb_appliances
                 WHERE household_id=v_household AND name='Demo air conditioner') THEN
    INSERT INTO public.lb_appliances
      (household_id,name,quantity,power_kw,hours_per_day,rating_is_measured,notes)
    VALUES (v_household,'Demo air conditioner',1,1.2,3,false,
            'Synthetic scenario only; rating and daily hours are assumptions');
  END IF;

  -- One fictional grocery purchase. Inserted once, and only a newly inserted receipt
  -- updates the pantry. This avoids double spending or double stock on repeat runs.
  INSERT INTO public.grocery_receipts
    (household_id,source_identifier,retailer,receipt_date,total,currency,
     amount_scope,full_receipt_total_mur)
  VALUES (v_household,'livebetter-seed-05-receipt','LiveBetter Fictional Store',
          '2026-10-10'::date,233,'MUR','full_receipt',233)
  ON CONFLICT (household_id,source_identifier) DO NOTHING
  RETURNING id INTO v_receipt;

  IF v_receipt IS NOT NULL THEN
    FOR v_item IN SELECT value FROM jsonb_array_elements(v_items) LOOP
      INSERT INTO public.receipt_items
        (receipt_id,original_name,normalized_name,quantity,unit,line_total)
      VALUES (v_receipt,v_item->>'original_name',v_item->>'normalized_name',
              (v_item->>'quantity')::numeric,v_item->>'unit',
              (v_item->>'line_total')::numeric);

      INSERT INTO public.pantry_items
        (household_id,ingredient_name,quantity,unit,available)
      VALUES (v_household,v_item->>'normalized_name',(v_item->>'quantity')::numeric,
              v_item->>'unit',true)
      ON CONFLICT (household_id,ingredient_name,unit)
      DO UPDATE SET quantity=public.pantry_items.quantity+EXCLUDED.quantity,
                    available=true,updated_at=now()
      RETURNING id INTO v_pantry_id;

      INSERT INTO public.pantry_events
        (household_id,pantry_item_id,quantity_delta,reason)
      VALUES (v_household,v_pantry_id,(v_item->>'quantity')::numeric,'demo_receipt_purchase');
    END LOOP;
    INSERT INTO public.activity_logs (household_id,event_type,related_entity_id,details)
    VALUES (v_household,'receipt_confirmed',v_receipt,
            '{"origin":"fictional_demo_seed_05","actual_purchase":false}'::jsonb);
  END IF;

  RAISE NOTICE 'Demo household id: %', v_household;
  RAISE NOTICE 'Owner email: %', v_owner_email;
END;
$seed$;
COMMIT;

-- Confirmation: returns the demo household and counts, without exposing others.
SELECT h.id, h.name, h.members,
  (SELECT count(*) FROM public.utility_bills b WHERE b.household_id=h.id) AS bill_count,
  (SELECT count(*) FROM public.grocery_receipts r WHERE r.household_id=h.id) AS receipt_count,
  (SELECT count(*) FROM public.pantry_items p WHERE p.household_id=h.id) AS pantry_item_count,
  (SELECT count(*) FROM public.lb_assessments a WHERE a.household_id=h.id) AS assessment_count
FROM public.households h
WHERE h.name='LiveBetter Demo Household - Seed 05'
  AND EXISTS (SELECT 1 FROM public.lb_utility_profiles p WHERE p.household_id=h.id);
-- Results may show more than one row only if several Auth users have created same-named demo households.
