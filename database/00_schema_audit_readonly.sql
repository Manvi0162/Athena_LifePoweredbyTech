-- READ ONLY: Run first in Supabase SQL Editor and inspect the results.
-- Confirm the original Food module tables, column types and functions.
SELECT table_name FROM information_schema.tables
 WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
 ORDER BY table_name;

SELECT table_name, ordinal_position, column_name, data_type, is_nullable, column_default
 FROM information_schema.columns
 WHERE table_schema='public' AND table_name IN
 ('households','utility_bills','meter_readings','grocery_receipts','receipt_items',
  'pantry_items','pantry_events','household_actions','activity_logs',
  'cooking_operations','lb_recipes','lb_recipe_ingredients','extracted_documents')
 ORDER BY table_name,ordinal_position;

SELECT n.nspname as schema_name, p.proname as function_name,
       pg_get_function_identity_arguments(p.oid) as signature
 FROM pg_proc p JOIN pg_namespace n on n.oid=p.pronamespace
 WHERE n.nspname='public' AND p.proname IN
 ('confirm_grocery_receipt','lb_confirm_cooking','lb_save_ai_recipe')
 ORDER BY function_name;

SELECT schemaname, tablename, rowsecurity
 FROM pg_tables WHERE schemaname='public' ORDER BY tablename;

SELECT schemaname, tablename, policyname, roles, cmd
 FROM pg_policies WHERE schemaname='public'
 ORDER BY tablename, policyname;
