-- LiveBetter integration: storage for the water and electricity engines.
-- Run once in the Supabase SQL Editor AFTER 01_livebetter_schema.sql and 02_lb_confirm_cooking_v2.sql.
-- Safe to run again. Does not change or drop existing tables or records.
--
-- Each engine keeps its detailed state (assessment versions, forecast snapshots, goals) as one JSON document
-- per household and module. Shared facts are still written to utility_bills, meter_readings,
-- household_actions and activity_logs, so food, Big Brain and dashboards read them as before.
BEGIN;

CREATE TABLE IF NOT EXISTS public.module_state (
  household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
  module text NOT NULL CHECK (module IN ('water', 'electricity')),
  state jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (household_id, module)
);

ALTER TABLE public.module_state ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Owners access module state" ON public.module_state;
CREATE POLICY "Owners access module state" ON public.module_state
  FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.households h WHERE h.id = household_id AND h.owner_id = (select auth.uid())))
  WITH CHECK (EXISTS (SELECT 1 FROM public.households h WHERE h.id = household_id AND h.owner_id = (select auth.uid())));

GRANT SELECT, INSERT, UPDATE, DELETE ON public.module_state TO authenticated;

COMMIT;
NOTIFY pgrst, 'reload schema';
