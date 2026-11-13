-- LIVEBETTER 06: COMPREHENSIVE, FICTIONAL, REPEATABLE DEMO SEED
-- Compatible with migrations 01, 02, 03, 04 from LiveBetter_Database_Package.
-- IMPORTANT: This script DOES NOT import the authentic UniTools recipe dataset.
-- It creates 6 clearly demo-labelled, manually specified Mauritian/Mauritian-inspired
-- recipe fixtures, marked verified ONLY for exercising the verified-recipe API path.
-- Import the genuine licensed dataset separately for the hackathon requirement.
-- DATA IS SYNTHETIC. Costs shown in old bills are NOT official tariff calculations.
-- Do NOT run on real household records. Creates an isolated dedicated demo household.
-- Rerunning is idempotent for this household: seeded IDs are stable, no double stock.
-- Requires an existing auth.users email. Change below before running in SQL Editor.

BEGIN;
DO $seed$
DECLARE
  v_email text := 'demo@livebetter.test'; -- CHANGE THIS
  v_owner uuid;
  v_h uuid;
  v_id uuid;
  v_rec uuid;
  v_receipt uuid;
  v_item jsonb;
  v_row record;
  v_bill record;
  v_ri record;
  v_ing record;
  v_pantry uuid;
  v_cook uuid;
  v_ai_run uuid;
  v_ai_rec uuid;
  v_forecast uuid;
  v_actual uuid;
  v_reading uuid;
  v_review uuid;
  v_added numeric;
  v_pantry_quantity numeric;
  v_month integer;
  v_day_start date;
  v_day_end date;
  v_kind text;
  v_units numeric;
  v_amount numeric;
  v_monthly_start date;
  v_recipe jsonb;
  v_recipes jsonb := '[
    {"slug":"vegetable_fried_rice","name":"Mauritian-inspired Vegetable Fried Rice (DEMO)","cuisine":"Mauritian-inspired","description":"Test fixture; rice stir-fried with vegetables and egg. Not imported from a licensed recipe dataset.","servings":4,"prep_minutes":15,"cook_minutes":15,"ingredients":[["rice",400,"g"],["carrot",200,"g"],["peas",150,"g"],["onion",120,"g"],["egg",2,"piece"],["cooking oil",20,"ml"]],"instructions":["Cook rice and cool it safely.","Dice carrot and onion; cook vegetables thoroughly.","Scramble eggs until fully cooked.","Stir-fry rice, vegetables and eggs, then serve hot."]},
    {"slug":"rougaille_tomates","name":"Rougaille Tomates (DEMO)","cuisine":"Mauritian","description":"Test fixture for a Mauritian tomato rougaille; proportions should be reviewed before real cooking.","servings":4,"prep_minutes":10,"cook_minutes":20,"ingredients":[["tomato",500,"g"],["onion",150,"g"],["garlic",10,"g"],["cooking oil",20,"ml"]],"instructions":["Wash and chop the tomatoes, onion and garlic.","Soften onion and garlic in a pan with oil.","Add tomato and simmer until the sauce thickens.","Season to taste and serve with rice or farata."]},
    {"slug":"lentil_dal","name":"Mauritian-style Lentil Dal (DEMO)","cuisine":"Mauritian-inspired","description":"Demo lentil dal fixture; not a sourced traditional recipe.","servings":4,"prep_minutes":10,"cook_minutes":30,"ingredients":[["lentils",250,"g"],["onion",100,"g"],["garlic",10,"g"],["tomato",150,"g"],["cooking oil",15,"ml"]],"instructions":["Rinse lentils and boil in clean water until tender.","Sauté onion and garlic until softened.","Add diced tomato; combine with cooked lentils.","Simmer, season to taste and serve hot."]},
    {"slug":"vegetable_mine_frite","name":"Vegetable Mine Frite (DEMO)","cuisine":"Mauritian-inspired","description":"Demo version of fried noodles with vegetables.","servings":4,"prep_minutes":15,"cook_minutes":15,"ingredients":[["noodles",400,"g"],["carrot",150,"g"],["cabbage",250,"g"],["onion",100,"g"],["cooking oil",25,"ml"]],"instructions":["Cook noodles according to packaging and drain.","Shred cabbage and slice carrot and onion.","Stir-fry vegetables until cooked.","Add noodles, toss well and serve immediately."]},
    {"slug":"farata","name":"Farata (DEMO)","cuisine":"Mauritian","description":"Simple flatbread demo fixture. Cooking water is untracked pantry input.","servings":4,"prep_minutes":25,"cook_minutes":15,"ingredients":[["flour",400,"g"],["cooking oil",30,"ml"]],"instructions":["Mix flour with water added gradually into a soft dough.","Rest the dough; divide and roll into flat rounds.","Apply a little oil and cook both sides on a hot pan.","Serve with dal or rougaille."]},
    {"slug":"chayote_saute","name":"Chouchou Sauté (DEMO)","cuisine":"Mauritian-inspired","description":"Demo vegetable preparation using chayote, also called chouchou.","servings":4,"prep_minutes":15,"cook_minutes":20,"ingredients":[["chayote",600,"g"],["onion",100,"g"],["garlic",10,"g"],["cooking oil",15,"ml"]],"instructions":["Peel and dice the chayote safely.","Sauté onion and garlic in oil.","Add chayote and cook until tender, adding water if required.","Season and serve as a side dish."]}
  ]'::jsonb;
  v_purchases jsonb := '[
    {"ref":"receipt-a","date":"2026-11-05","store":"LiveBetter Synthetic Shop A","items":[["RICE 2KG","rice",2000,"g",130],["CARROT 1KG","carrot",1000,"g",65],["PEAS 500G","peas",500,"g",90],["ONION 1KG","onion",1000,"g",75],["EGGS 12","egg",12,"piece",105],["OIL 1L","cooking oil",1000,"ml",110],["TOMATO 1.5KG","tomato",1500,"g",150],["GARLIC 200G","garlic",200,"g",45],["LENTILS 1KG","lentils",1000,"g",120]]},
    {"ref":"receipt-b","date":"2026-11-07","store":"LiveBetter Synthetic Shop B","items":[["NOODLES 1KG","noodles",1000,"g",160],["CABBAGE 1KG","cabbage",1000,"g",60],["FLOUR 2KG","flour",2000,"g",95],["CHOUCHOU 1KG","chayote",1000,"g",70],["BANANAS 6","banana",6,"piece",65]]}
  ]'::jsonb;
BEGIN
  IF v_email = 'REPLACE_WITH_YOUR_AUTH_EMAIL' THEN
    RAISE EXCEPTION 'Change v_email to an actual registered email in auth.users before running.';
  END IF;
  SELECT id INTO v_owner FROM auth.users WHERE lower(email) = lower(v_email) LIMIT 1;
  IF v_owner IS NULL THEN
    RAISE EXCEPTION 'No Supabase Auth user matches %. Create the user in Authentication -> Users first.', v_email;
  END IF;

  -- All demo IDs derive from auth user ID, so repeats are safe and isolated.
  v_h := md5('lb-full-demo-06:household:' || v_owner::text)::uuid;
  INSERT INTO public.households(id, owner_id, name, members, currency, preferences, budget_goals)
  VALUES (v_h, v_owner, 'LiveBetter Full Demo - Seed 06', 4, 'MUR',
    '{"diet":"mixed","allergies":[],"servings":4,"demo_data":true,"allergy_status":"unknown"}'::jsonb,
    '{"groceries":12000,"water":500,"electricity":2500}'::jsonb)
  ON CONFLICT(id) DO NOTHING;
  IF NOT EXISTS(SELECT 1 FROM public.households WHERE id=v_h AND owner_id=v_owner) THEN
    RAISE EXCEPTION 'Demo household ID collision or ownership mismatch';
  END IF;

  INSERT INTO public.lb_user_preferences(user_id,preferred_language,privacy_consent_at)
  VALUES (v_owner,'en',NULL) ON CONFLICT(user_id) DO NOTHING;
  INSERT INTO public.lb_household_modules(household_id,module,enabled,setup_status)
  VALUES (v_h,'food',true,'ready'),(v_h,'water',true,'ready'),(v_h,'electricity',true,'ready')
  ON CONFLICT(household_id,module) DO NOTHING;
  INSERT INTO public.lb_assessments(household_id,module,version,answers,completed)
  VALUES
    (v_h,'general',1,'{"household_members":4,"home_type":"house","occupancy":"most_of_day","main_goal":"all_of_the_above","demo_data":true}'::jsonb,true),
    (v_h,'water',1,'{"shower_duration":"5-10 min","flushes_per_person":"4-6","laundry_loads_per_week":"3-5","outdoor_water_use":"about_weekly","expected_change":"no","demo_data":true}'::jsonb,true),
    (v_h,'electricity',1,'{"major_appliances":["air_conditioner","refrigerator","washing_machine"],"ac_hours_per_day":"1-3 h","water_heating":"electric","cooking_energy":"gas","expected_change":"no","demo_data":true}'::jsonb,true),
    (v_h,'food',1,'{"home_cooked_meals":"2","diet":"mixed","allergies":"unsure","grocery_frequency":"weekly","main_challenge":"food_expiring","demo_data":true}'::jsonb,true)
  ON CONFLICT(household_id,module,version) DO NOTHING;
  INSERT INTO public.lb_utility_profiles(household_id,kind,tariff_code,monthly_budget_mur,profile)
  VALUES (v_h,'water',NULL,500,'{"source":"synthetic_demo","tariff_unverified":true,"billing_cycle":"monthly"}'::jsonb),
         (v_h,'electricity',NULL,2500,'{"source":"synthetic_demo","tariff_unverified":true,"billing_cycle":"monthly"}'::jsonb)
  ON CONFLICT(household_id,kind) DO NOTHING;

  -- Four COMPLETE, historical billing cycles for both utilities.
  -- The bill amounts are mock inputs, NOT official tariff-derived amounts.
  FOR v_month IN 7..10 LOOP
    v_day_start := make_date(2026,v_month,1);
    v_day_end := (v_day_start + interval '1 month - 1 day')::date;
    FOREACH v_kind IN ARRAY ARRAY['water','electricity'] LOOP
      IF v_kind = 'water' THEN
        v_units := (ARRAY[16.0,17.0,18.0,19.0])[v_month-6];
        v_amount := (ARRAY[380,400,420,450])[v_month-6];
      ELSE
        v_units := (ARRAY[230,245,260,275])[v_month-6];
        v_amount := (ARRAY[1550,1650,1770,1890])[v_month-6];
      END IF;
      v_id := md5(v_h::text || ':bill:' || v_kind || ':' || v_month::text)::uuid;
      INSERT INTO public.utility_bills(
        id,household_id,kind,period_start,period_end,units,amount,tariff_code,source_metadata)
      VALUES (v_id,v_h,v_kind,v_day_start,v_day_end,v_units,v_amount,NULL,
        jsonb_build_object('source','seed_06_synthetic','measured',false,'official_tariff',false))
      ON CONFLICT(id) DO NOTHING;
    END LOOP;
  END LOOP;
  -- Two readings per utility, all manually entered fictional meter readings.
  FOR v_row IN SELECT * FROM (VALUES
    ('water'::text,'2026-11-01T08:00:00+04'::timestamptz,500.0::numeric),
    ('water','2026-11-11T08:00:00+04'::timestamptz,506.2::numeric),
    ('electricity','2026-11-01T08:00:00+04'::timestamptz,12000.0::numeric),
    ('electricity','2026-11-11T08:00:00+04'::timestamptz,12088.0::numeric)
  ) AS x(kind,captured_at,reading) LOOP
    v_id := md5(v_h::text || ':meter:' || v_row.kind || ':' || v_row.captured_at::text)::uuid;
    INSERT INTO public.meter_readings(id,household_id,kind,reading,captured_at)
    VALUES(v_id,v_h,v_row.kind,v_row.reading,v_row.captured_at)
    ON CONFLICT(id) DO NOTHING;
  END LOOP;

  FOR v_row IN SELECT * FROM (VALUES
    ('Demo air conditioner'::text,1,1.2::numeric,3.0::numeric),
    ('Demo refrigerator',1,0.15::numeric,24.0::numeric),
    ('Demo washing machine',1,0.5::numeric,0.6::numeric)
  ) x(name,quantity,power_kw,hours_per_day) LOOP
    v_id := md5(v_h::text || ':appliance:' || v_row.name)::uuid;
    INSERT INTO public.lb_appliances(id,household_id,name,quantity,power_kw,hours_per_day,rating_is_measured,notes)
    VALUES(v_id,v_h,v_row.name,v_row.quantity,v_row.power_kw,v_row.hours_per_day,false,
      'Demo assumptions only; not independently measured')
    ON CONFLICT(id) DO NOTHING;
  END LOOP;

  -- OCR proposals for water/electricity and groceries. Proposals are not authoritative.
  FOR v_row IN SELECT * FROM (VALUES
    ('water_bill'::text,'seed06-water-oct', 'demo_water_oct.png', 'confirmed'::text),
    ('electricity_bill','seed06-electricity-oct', 'demo_electricity_oct.png','confirmed'),
    ('grocery_receipt','seed06-receipt-pending','demo_receipt_pending.png','pending_review')
  ) x(kind,source_identifier,source_filename,status) LOOP
    v_id := md5(v_h::text || ':review:' || v_row.source_identifier)::uuid;
    INSERT INTO public.lb_document_reviews(
      id,household_id,kind,source_identifier,source_filename,proposed_fields,
      uncertain_parts,status,reviewed_at)
    VALUES(v_id,v_h,v_row.kind,v_row.source_identifier,v_row.source_filename,
      jsonb_build_object('synthetic',true,'requires_real_photo',true), '[]'::jsonb,
      v_row.status,CASE WHEN v_row.status='confirmed' THEN now() ELSE NULL END)
    ON CONFLICT(id) DO NOTHING;
  END LOOP;
  -- Attach the confirmed October review to its matching seeded bill (only).
  FOREACH v_kind IN ARRAY ARRAY['water','electricity'] LOOP
    v_id := md5(v_h::text || ':review:seed06-' || v_kind || '-oct')::uuid;
    UPDATE public.utility_bills
    SET document_review_id=v_id
    WHERE id=md5(v_h::text || ':bill:' || v_kind || ':10')::uuid
      AND document_review_id IS NULL;
  END LOOP;

  -- Synthetic OCR sandbox record. Legacy extracted_documents has no household_id
  -- and is intentionally not readable to signed-in clients under migrations 01-04.
  INSERT INTO public.extracted_documents(
    source_filename,image_sha256,document_type,raw_text,fields,uncertain_parts,review_status)
  VALUES('seed06_synthetic_grocery_receipt.txt',md5('lb-seed06-doc:'||v_h::text),
    'receipt','DEMO DOCUMENT ONLY - NO REAL RECEIPT',
    '[{"name":"document_source","value":"seed_06_synthetic"}]'::jsonb,
    '[]'::jsonb,'pending_review')
  ON CONFLICT(image_sha256) DO NOTHING;

  -- Purchases + receipt items + pantry additions. Each receipt ID is fixed, so
  -- second execution does not re-add inventory or duplicate spending.
  FOR v_item IN SELECT value FROM jsonb_array_elements(v_purchases) LOOP
    v_receipt := NULL;
    v_id := md5(v_h::text || ':' || (v_item->>'ref'))::uuid;
    INSERT INTO public.grocery_receipts(
      id,household_id,source_identifier,retailer,receipt_date,total,currency,
      amount_scope,full_receipt_total_mur)
    SELECT v_id,v_h, 'livebetter-seed06-' || (v_item->>'ref'),
      v_item->>'store',(v_item->>'date')::date,
      (SELECT SUM((line->>4)::numeric) FROM jsonb_array_elements(v_item->'items') AS t(line)),
      'MUR','full_receipt',
      (SELECT SUM((line->>4)::numeric) FROM jsonb_array_elements(v_item->'items') AS t(line))
    ON CONFLICT(household_id,source_identifier) DO NOTHING
    RETURNING id INTO v_receipt;
    IF v_receipt IS NOT NULL THEN
      FOR v_ri IN SELECT value AS line FROM jsonb_array_elements(v_item->'items') LOOP
        v_rec := md5(v_receipt::text || ':line:' || (v_ri.line->>1))::uuid;
        INSERT INTO public.receipt_items(id,receipt_id,original_name,normalized_name,quantity,unit,line_total)
        VALUES(v_rec,v_receipt,v_ri.line->>0,v_ri.line->>1,(v_ri.line->>2)::numeric,
          v_ri.line->>3,(v_ri.line->>4)::numeric)
        ON CONFLICT(id) DO NOTHING;
        INSERT INTO public.pantry_items(household_id,ingredient_name,quantity,unit,available)
        VALUES(v_h,v_ri.line->>1,(v_ri.line->>2)::numeric,v_ri.line->>3,true)
        ON CONFLICT(household_id,ingredient_name,unit)
        DO UPDATE SET quantity=public.pantry_items.quantity+EXCLUDED.quantity,
                      available=true,updated_at=now()
        RETURNING id INTO v_pantry;
        INSERT INTO public.pantry_events(household_id,pantry_item_id,quantity_delta,reason)
        VALUES(v_h,v_pantry,(v_ri.line->>2)::numeric,'demo_receipt_purchase');
      END LOOP;
      INSERT INTO public.activity_logs(household_id,event_type,related_entity_id,details)
      VALUES(v_h,'receipt_confirmed',v_receipt,
        jsonb_build_object('origin','seed_06_synthetic','actual_purchase',false));
    END IF;
  END LOOP;

  -- Six complete, queryable recipe fixtures; confirmed by SQL for API demo only.
  -- Household-private to avoid polluting the global verified dataset.
  FOR v_recipe IN SELECT value FROM jsonb_array_elements(v_recipes) LOOP
    v_rec := md5(v_h::text || ':recipe:' || (v_recipe->>'slug'))::uuid;
    INSERT INTO public.lb_recipes(
      id,household_id,name,cuisine,description,servings,source_type,
      verification_status,source_url,youtube_url,prep_minutes,cook_minutes,instructions)
    VALUES(v_rec,v_h,v_recipe->>'name',v_recipe->>'cuisine',v_recipe->>'description',
      (v_recipe->>'servings')::integer,'curated','verified',NULL,NULL,
      (v_recipe->>'prep_minutes')::integer,(v_recipe->>'cook_minutes')::integer,
      v_recipe->'instructions')
    ON CONFLICT(id) DO NOTHING;
    FOR v_ing IN SELECT value AS ing, ordinality AS num
      FROM jsonb_array_elements(v_recipe->'ingredients') WITH ORDINALITY LOOP
      v_id := md5(v_rec::text || ':ingredient:' || v_ing.num::text)::uuid;
      INSERT INTO public.lb_recipe_ingredients(
        id,recipe_id,ingredient_name,quantity,unit,optional)
      VALUES(v_id,v_rec,v_ing.ing->>0,(v_ing.ing->>1)::numeric,v_ing.ing->>2,false)
      ON CONFLICT(id) DO NOTHING;
    END LOOP;
  END LOOP;

  -- Demonstrate a completed cooking transaction, with consistent stock ledger.
  -- Rougaille uses 500 g tomatoes, 150 g onion, 10 g garlic and 20 ml oil.
  v_rec := md5(v_h::text || ':recipe:rougaille_tomates')::uuid;
  v_cook := md5(v_h::text || ':operation:demo-rougaille-cooked-once')::uuid;
  v_id := NULL;
  INSERT INTO public.cooking_operations(id,household_id,recipe_id)
  VALUES(v_cook,v_h,v_rec::text)
  ON CONFLICT(id) DO NOTHING RETURNING id INTO v_id;
  IF v_id IS NOT NULL THEN
    FOR v_ing IN
      SELECT lower(btrim(ingredient_name)) AS ingredient_name,
             lower(btrim(unit)) AS unit, SUM(quantity) AS quantity
      FROM public.lb_recipe_ingredients WHERE recipe_id=v_rec AND optional=false
      GROUP BY lower(btrim(ingredient_name)), lower(btrim(unit))
    LOOP
      v_pantry := NULL;
      UPDATE public.pantry_items
      SET quantity=quantity-v_ing.quantity,
          available=(quantity-v_ing.quantity)>0, updated_at=now()
      WHERE household_id=v_h AND ingredient_name=v_ing.ingredient_name
        AND unit=v_ing.unit AND quantity>=v_ing.quantity
      RETURNING id INTO v_pantry;
      IF v_pantry IS NULL THEN
        RAISE EXCEPTION 'Insufficient demo stock to cook %', v_ing.ingredient_name;
      END IF;
      INSERT INTO public.pantry_events(
        household_id,pantry_item_id,quantity_delta,reason,operation_id)
      VALUES(v_h,v_pantry,-v_ing.quantity,'recipe_cooked',v_cook);
    END LOOP;
    INSERT INTO public.activity_logs(household_id,event_type,related_entity_id,details)
    VALUES(v_h,'recipe_cooked',v_rec,
      jsonb_build_object('operation_id',v_cook,'origin','seed_06_synthetic'));
  END IF;

  -- A forecast for October (backtest against October actual), and November outlook.
  -- Calculation only uses synthetic observed units and normalized cycle length.
  FOREACH v_kind IN ARRAY ARRAY['water','electricity'] LOOP
    v_units := CASE WHEN v_kind='water' THEN 18 ELSE 260 END;
    -- September has 30 days, October has 31 days.
    v_forecast := md5(v_h::text || ':forecast:' || v_kind || ':oct-backtest')::uuid;
    INSERT INTO public.lb_utility_forecasts(
      id,household_id,kind,period_start,period_end,status,estimated_units,unit,
      estimated_cost_mur,confidence,method,source_bill_ids,evidence,assumptions,tariff_source)
    VALUES(v_forecast,v_h,v_kind,'2026-10-01','2026-11-01','preliminary',
      round(v_units / 30 * 31,3),CASE WHEN v_kind='water' THEN 'm3' ELSE 'kWh' END,
      NULL,'low','historical_daily_baseline',
      ARRAY[md5(v_h::text || ':bill:' || v_kind || ':9')::uuid],
      jsonb_build_object('source','seed_06_synthetic','previous_cycle_units',v_units,'previous_cycle_days',30),
      '{"cycle_days":31,"unchanged_use":true,"synthetic":true}'::jsonb,
      '{"status":"not_calculated","tariff_unverified":true}'::jsonb)
    ON CONFLICT(id) DO NOTHING;
    v_actual := md5(v_h::text || ':bill:' || v_kind || ':10')::uuid;
    v_units := CASE WHEN v_kind='water' THEN 19 ELSE 275 END;
    v_id := md5(v_h::text || ':forecast-check:' || v_kind || ':oct')::uuid;
    INSERT INTO public.lb_forecast_checks(id,household_id,forecast_id,actual_bill_id,actual_units,error_pct)
    VALUES(v_id,v_h,v_forecast,v_actual,v_units,
      round(abs(v_units - (CASE WHEN v_kind='water' THEN 18 ELSE 260 END)::numeric/30*31)
            /NULLIF(v_units,0)*100,4))
    ON CONFLICT(id) DO NOTHING;
    v_forecast := md5(v_h::text || ':forecast:' || v_kind || ':nov')::uuid;
    -- Oct has 31 days; Nov has 30 days.
    INSERT INTO public.lb_utility_forecasts(
      id,household_id,kind,period_start,period_end,status,estimated_units,unit,
      estimated_cost_mur,confidence,method,source_bill_ids,evidence,assumptions,tariff_source)
    VALUES(v_forecast,v_h,v_kind,'2026-11-01','2026-12-01','better_supported',
      round(v_units/31*30,3),CASE WHEN v_kind='water' THEN 'm3' ELSE 'kWh' END,
      NULL,'medium','historical_daily_baseline',
      ARRAY[md5(v_h::text || ':bill:' || v_kind || ':10')::uuid],
      jsonb_build_object('source','seed_06_synthetic','previous_cycle_units',v_units,'previous_cycle_days',31),
      '{"cycle_days":30,"unchanged_use":true,"synthetic":true}'::jsonb,
      '{"status":"not_calculated","tariff_unverified":true}'::jsonb)
    ON CONFLICT(id) DO NOTHING;
  END LOOP;

  -- What-if scenario math: AC 1.2 kW x 1h/day x 15 days = 18 kWh.
  -- Monetary savings deliberately NULL without verified tariff classification.
  INSERT INTO public.lb_scenarios(
    id,household_id,module,action_code,period_start,period_end,status,inputs,
    assumptions,baseline_units,scenario_units,baseline_cost_mur,
    scenario_cost_mur,estimated_savings_mur)
  VALUES
    (md5(v_h::text || ':scenario:ac')::uuid,v_h,'electricity','reduce_ac_usage',
      '2026-11-01','2026-12-01','saved',
      '{"appliance":"Demo air conditioner","reduce_hours_per_day":1,"days":15}'::jsonb,
      '{"power_kw":1.2,"power_is_measured":false,"synthetic":true}'::jsonb,
      round(275.0/31*30,3),round(275.0/31*30-18,3),NULL,NULL,NULL),
    (md5(v_h::text || ':scenario:water')::uuid,v_h,'water','shorter_showers',
      '2026-11-01','2026-12-01','draft',
      '{"minutes_saved_per_person_per_day":2,"persons":4,"days":30}'::jsonb,
      '{"assumed_flow_l_per_min":8,"synthetic":true}'::jsonb,
      round(19.0/31*30,3),round(19.0/31*30-1.92,3),NULL,NULL,NULL),
    (md5(v_h::text || ':scenario:food')::uuid,v_h,'food','pantry_first_meal',
      '2026-11-01','2026-12-01','draft',
      '{"recipe":"Mauritian-inspired Vegetable Fried Rice (DEMO)"}'::jsonb,
      '{"no_purchase_assumed":true,"savings_unknown":true,"synthetic":true}'::jsonb,
      NULL,NULL,NULL,NULL,NULL)
  ON CONFLICT(id) DO NOTHING;

  -- Seeded output EXAMPLE, NOT an actual Gemini execution.
  v_ai_run := md5(v_h::text || ':ai:example')::uuid;
  INSERT INTO public.lb_ai_runs(
    id,household_id,status,model_name,module_status,module_summaries,
    decision_context,dashboard)
  VALUES(v_ai_run,v_h,'partial',NULL,
    '{"food":"data_available","water":"demo_data","electricity":"demo_data"}'::jsonb,
    '{"food":{"status":"demo_inventory"},"water":{"status":"synthetic_baseline"},"electricity":{"status":"synthetic_baseline"}}'::jsonb,
    '{"origin":"seed_06_synthetic","not_a_real_ai_execution":true,"currency":"MUR","tariff_verified":false}'::jsonb,
    '{"status":"partial","summary":"Synthetic dashboard fixture for integration testing only","generated_by_gemini":false}'::jsonb)
  ON CONFLICT(id) DO NOTHING;
  FOR v_row IN SELECT * FROM (VALUES
    ('domain'::text,'food'::text,'use_pantry_ingredients'::text,'Cook with ingredients already in the pantry'::text,3.8::numeric),
    ('domain','water','review_shower_scenario','Compare a hypothetical shorter-shower scenario',3.0),
    ('domain','electricity','reduce_ac_usage','Review the air-conditioner runtime scenario',3.3),
    ('big_brain','food','confirm_receipts','Verify scanned receipts before accepting spend totals',3.6)
  ) x(source,module,action_id,title,score) LOOP
    v_id := md5(v_ai_run::text || ':' || v_row.source || ':' || v_row.module || ':' || v_row.action_id)::uuid;
    INSERT INTO public.lb_ai_recommendations(
      id,run_id,household_id,source,module,action_id,title,
      estimated_savings_mur,confidence,evidence,assumptions,priority_score,explanation)
    VALUES(v_id,v_ai_run,v_h,v_row.source,v_row.module,v_row.action_id,
      v_row.title,NULL,'low',
      '{"origin":"synthetic_seed_06","actual_savings_measured":false}'::jsonb,
      '{"illustrative_only":true}'::jsonb,v_row.score,
      'Example explanation for UI testing. No verified household savings are claimed.')
    ON CONFLICT(id) DO NOTHING;
  END LOOP;
  v_ai_rec := md5(v_ai_run::text || ':domain:electricity:reduce_ac_usage')::uuid;
  v_id := md5(v_h::text || ':household-action:ac')::uuid;
  INSERT INTO public.household_actions(
    id,household_id,action_type,assumptions,status,recommendation_id,scenario_id)
  VALUES(v_id,v_h,'reduce_ac_usage','{"synthetic_demo":true}'::jsonb,
    'selected',v_ai_rec,md5(v_h::text || ':scenario:ac')::uuid)
  ON CONFLICT(id) DO NOTHING;
  v_id := md5(v_h::text || ':activity:ai-seed')::uuid;
  INSERT INTO public.activity_logs(id,household_id,event_type,related_entity_id,details)
  VALUES(v_id,v_h,'insights_generated',v_ai_run,
    '{"origin":"seed_06_synthetic","not_real_gemini_execution":true}'::jsonb)
  ON CONFLICT(id) DO NOTHING;

  RAISE NOTICE 'LiveBetter FULL DEMO seeded for % (household_id = %)',v_email,v_h;
  RAISE NOTICE 'All sample data are synthetic. Recipes are curated demo fixtures, not imported dataset.';
END;
$seed$;
COMMIT;

-- Overview of ALL public table counts for the demo household. The legacy OCR
-- table is global and intentionally not connected to a household.
WITH demo AS (
  SELECT h.id FROM public.households h JOIN auth.users u ON u.id=h.owner_id
  WHERE lower(u.email)=lower('demo@livebetter.test')
    AND h.name='LiveBetter Full Demo - Seed 06'
)
SELECT 'households' AS table_name, count(*) AS demo_rows FROM public.households WHERE id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_household_modules',count(*) FROM public.lb_household_modules WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_assessments',count(*) FROM public.lb_assessments WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_utility_profiles',count(*) FROM public.lb_utility_profiles WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'utility_bills',count(*) FROM public.utility_bills WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'meter_readings',count(*) FROM public.meter_readings WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_appliances',count(*) FROM public.lb_appliances WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_document_reviews',count(*) FROM public.lb_document_reviews WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'grocery_receipts',count(*) FROM public.grocery_receipts WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'receipt_items',count(*) FROM public.receipt_items WHERE receipt_id IN (SELECT id FROM public.grocery_receipts WHERE household_id IN (SELECT id FROM demo))
UNION ALL SELECT 'pantry_items',count(*) FROM public.pantry_items WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'pantry_events',count(*) FROM public.pantry_events WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'cooking_operations',count(*) FROM public.cooking_operations WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_recipes',count(*) FROM public.lb_recipes WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_recipe_ingredients',count(*) FROM public.lb_recipe_ingredients WHERE recipe_id IN (SELECT id FROM public.lb_recipes WHERE household_id IN (SELECT id FROM demo))
UNION ALL SELECT 'lb_utility_forecasts',count(*) FROM public.lb_utility_forecasts WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_forecast_checks',count(*) FROM public.lb_forecast_checks WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_scenarios',count(*) FROM public.lb_scenarios WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_ai_runs',count(*) FROM public.lb_ai_runs WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_ai_recommendations',count(*) FROM public.lb_ai_recommendations WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'household_actions',count(*) FROM public.household_actions WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'activity_logs',count(*) FROM public.activity_logs WHERE household_id IN (SELECT id FROM demo)
UNION ALL SELECT 'lb_user_preferences',count(*) FROM public.lb_user_preferences WHERE user_id IN (SELECT owner_id FROM public.households WHERE id IN (SELECT id FROM demo))
UNION ALL SELECT 'extracted_documents (synthetic only)',count(*) FROM public.extracted_documents WHERE source_filename='seed06_synthetic_grocery_receipt.txt'
ORDER BY table_name;
