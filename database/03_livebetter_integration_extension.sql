-- LiveBetter integration extension - 13 Nov 2026
-- Apply only AFTER the Food module's 01_livebetter_schema.sql and
-- 02_lb_confirm_cooking_v2.sql, or an equivalent existing base schema.
-- Adds shared tables for onboarding, utilities, forecasts and Big Brain.
-- No DROP TABLE, DELETE, or changes to existing Food RPC signatures.
-- REVIEW THE SCHEMA AUDIT BEFORE APPLYING TO A PRODUCTION DATABASE.

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Supabase Auth owns credentials. Never store passwords in these tables.
CREATE TABLE IF NOT EXISTS public.lb_user_preferences (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    preferred_language text NOT NULL DEFAULT 'en'
        CHECK (preferred_language IN ('en', 'fr', 'mfe')),
    privacy_consent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Each household can enable modules independently.
CREATE TABLE IF NOT EXISTS public.lb_household_modules (
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    module text NOT NULL CHECK (module IN ('food', 'water', 'electricity')),
    enabled boolean NOT NULL DEFAULT true,
    setup_status text NOT NULL DEFAULT 'not_started'
        CHECK (setup_status IN ('not_started', 'in_progress', 'ready')),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (household_id, module)
);

-- Four general questions + five optional questions per specialist.
-- Every edit can be a new version. Unknown / skipped answers remain absent.
CREATE TABLE IF NOT EXISTS public.lb_assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    module text NOT NULL
        CHECK (module IN ('general', 'food', 'water', 'electricity')),
    version integer NOT NULL CHECK (version >= 1),
    answers jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(answers) = 'object'),
    completed boolean NOT NULL DEFAULT false,
    effective_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (household_id, module, version)
);

-- Other domain-specific settings not covered by the general assessment.
CREATE TABLE IF NOT EXISTS public.lb_utility_profiles (
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('water', 'electricity')),
    tariff_code text,
    monthly_budget_mur numeric(12,2)
        CHECK (monthly_budget_mur IS NULL OR monthly_budget_mur >= 0),
    profile jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(profile) = 'object'),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (household_id, kind)
);

-- Optional measured/estimated device configuration for electricity what-if.
CREATE TABLE IF NOT EXISTS public.lb_appliances (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    quantity integer NOT NULL DEFAULT 1 CHECK (quantity > 0),
    power_kw numeric(10,4)
        CHECK (power_kw IS NULL OR power_kw > 0),
    hours_per_day numeric(6,2)
        CHECK (hours_per_day IS NULL OR (hours_per_day >= 0 AND hours_per_day <= 24)),
    rating_is_measured boolean NOT NULL DEFAULT false,
    notes text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Household-scoped OCR review records, separate from authoritative bills or receipts.
-- Does not modify or expose the legacy extracted_documents table.
CREATE TABLE IF NOT EXISTS public.lb_document_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    kind text NOT NULL
        CHECK (kind IN ('water_bill', 'electricity_bill', 'grocery_receipt')),
    source_identifier text NOT NULL CHECK (length(btrim(source_identifier)) > 0),
    source_filename text,
    proposed_fields jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(proposed_fields) = 'object'),
    uncertain_parts jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(uncertain_parts) = 'array'),
    status text NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review', 'confirmed', 'rejected')),
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (household_id, kind, source_identifier),
    UNIQUE (id, household_id)
);

-- Preserve recorded utility amounts as unknown if the bill shows only usage.
-- Existing utility_bills.amount from the base SQL was NOT NULL.
ALTER TABLE public.utility_bills ALTER COLUMN amount DROP NOT NULL;
ALTER TABLE public.utility_bills
    ADD COLUMN IF NOT EXISTS verified_at timestamptz,
    ADD COLUMN IF NOT EXISTS start_meter_reading numeric(14,3),
    ADD COLUMN IF NOT EXISTS end_meter_reading numeric(14,3),
    ADD COLUMN IF NOT EXISTS document_review_id uuid,
    ADD COLUMN IF NOT EXISTS source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Existing receipt totals differ between OCR whole-receipt and Food-only flows.
-- Do not assume old records are Food-only; a later reviewed migration can label them.
ALTER TABLE public.grocery_receipts
    ADD COLUMN IF NOT EXISTS amount_scope text NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS full_receipt_total_mur numeric(12,2);

CREATE UNIQUE INDEX IF NOT EXISTS lb_utility_bill_household_pair
    ON public.utility_bills(id, household_id);
-- Future forecast snapshots. A missing forecast must retain NULL quantities/costs.
CREATE TABLE IF NOT EXISTS public.lb_utility_forecasts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('water','electricity')),
    period_start date NOT NULL,
    period_end date NOT NULL CHECK (period_end > period_start),
    status text NOT NULL CHECK (status IN
        ('insufficient_data', 'preliminary', 'better_supported')),
    estimated_units numeric(14,3) CHECK (estimated_units IS NULL OR estimated_units >= 0),
    unit text NOT NULL CHECK (unit IN ('m3','kWh')),
    estimated_cost_mur numeric(12,2)
        CHECK (estimated_cost_mur IS NULL OR estimated_cost_mur >= 0),
    low_units numeric(14,3),
    high_units numeric(14,3),
    low_cost_mur numeric(12,2),
    high_cost_mur numeric(12,2),
    confidence text CHECK (confidence IN ('low','medium','high','good')),
    method text,
    source_bill_ids uuid[] NOT NULL DEFAULT '{}'::uuid[],
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    assumptions jsonb NOT NULL DEFAULT '{}'::jsonb,
    tariff_source jsonb NOT NULL DEFAULT '{}'::jsonb,
    generated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, household_id),
    CHECK ((kind = 'water' AND unit = 'm3')
        OR (kind = 'electricity' AND unit = 'kWh')),
    CHECK (status <> 'insufficient_data' OR estimated_units IS NULL)
);

-- Forecast predictions are checked against a real, later bill.
CREATE TABLE IF NOT EXISTS public.lb_forecast_checks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    forecast_id uuid NOT NULL,
    actual_bill_id uuid NOT NULL,
    actual_units numeric(14,3) NOT NULL CHECK (actual_units >= 0),
    error_pct numeric(12,4),
    checked_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (forecast_id, actual_bill_id),
    FOREIGN KEY (forecast_id, household_id)
        REFERENCES public.lb_utility_forecasts(id, household_id) ON DELETE CASCADE,
    FOREIGN KEY (actual_bill_id, household_id)
        REFERENCES public.utility_bills(id, household_id)
);

-- A hypothetical scenario never rewrites a real bill or pantry history.
CREATE TABLE IF NOT EXISTS public.lb_scenarios (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    module text NOT NULL
        CHECK (module IN ('food','water','electricity','combined')),
    action_code text,
    period_start date,
    period_end date,
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','saved','dismissed')),
    inputs jsonb NOT NULL DEFAULT '{}'::jsonb,
    assumptions jsonb NOT NULL DEFAULT '{}'::jsonb,
    baseline_units numeric(14,3),
    scenario_units numeric(14,3),
    baseline_cost_mur numeric(12,2),
    scenario_cost_mur numeric(12,2),
    estimated_savings_mur numeric(12,2),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, household_id),
    CHECK (period_start IS NULL OR period_end IS NULL OR period_end > period_start)
);

-- Each Big Brain execution has one reproducible evidence snapshot.
CREATE TABLE IF NOT EXISTS public.lb_ai_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id uuid NOT NULL REFERENCES public.households(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'partial'
        CHECK (status IN ('success','partial','failed')),
    model_name text,
    module_status jsonb NOT NULL DEFAULT '{}'::jsonb,
    module_summaries jsonb NOT NULL DEFAULT '{}'::jsonb,
    decision_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    dashboard jsonb NOT NULL DEFAULT '{}'::jsonb,
    generated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (id, household_id)
);

-- One normalized recommendation per source/module/action within one run.
-- estimated_savings_mur stays NULL if the calculation is not supported.
CREATE TABLE IF NOT EXISTS public.lb_ai_recommendations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL,
    household_id uuid NOT NULL,
    source text NOT NULL CHECK (source IN ('big_brain','domain')),
    module text NOT NULL CHECK (module IN ('food','water','electricity')),
    action_id text NOT NULL CHECK (length(btrim(action_id)) > 0),
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    estimated_savings_mur numeric(12,2)
        CHECK (estimated_savings_mur IS NULL OR estimated_savings_mur >= 0),
    confidence text CHECK (confidence IN ('low','medium','high')),
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    assumptions jsonb NOT NULL DEFAULT '{}'::jsonb,
    period_start date,
    period_end date,
    priority_score numeric(12,4),
    explanation text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, source, module, action_id),
    UNIQUE (id, household_id),
    FOREIGN KEY (run_id, household_id)
        REFERENCES public.lb_ai_runs(id, household_id) ON DELETE CASCADE,
    CHECK (period_start IS NULL OR period_end IS NULL OR period_end > period_start)
);

-- Existing household_actions is the lifecycle of selected/completed proposals.
ALTER TABLE public.household_actions
    ADD COLUMN IF NOT EXISTS recommendation_id uuid,
    ADD COLUMN IF NOT EXISTS scenario_id uuid,
    ADD COLUMN IF NOT EXISTS completed_at timestamptz,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

-- Cross-household references must fail even when IDs are known.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.household_actions'::regclass
          AND conname = 'lb_actions_recommendation_household_fk'
    ) THEN
        ALTER TABLE public.household_actions
          ADD CONSTRAINT lb_actions_recommendation_household_fk
          FOREIGN KEY (recommendation_id, household_id)
          REFERENCES public.lb_ai_recommendations(id, household_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.household_actions'::regclass
          AND conname = 'lb_actions_scenario_household_fk'
    ) THEN
        ALTER TABLE public.household_actions
          ADD CONSTRAINT lb_actions_scenario_household_fk
          FOREIGN KEY (scenario_id, household_id)
          REFERENCES public.lb_scenarios(id, household_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.utility_bills'::regclass
          AND conname = 'lb_bills_document_review_household_fk'
    ) THEN
        ALTER TABLE public.utility_bills
          ADD CONSTRAINT lb_bills_document_review_household_fk
          FOREIGN KEY (document_review_id, household_id)
          REFERENCES public.lb_document_reviews(id, household_id);
    END IF;
END $$;

-- Hot-path indexes for each household and timeline.
CREATE INDEX IF NOT EXISTS lb_assessments_latest_idx
    ON public.lb_assessments(household_id, module, version DESC);
CREATE INDEX IF NOT EXISTS lb_utility_bills_history_idx
    ON public.utility_bills(household_id, kind, period_end DESC);
CREATE INDEX IF NOT EXISTS lb_meter_readings_history_idx
    ON public.meter_readings(household_id, kind, captured_at DESC);
CREATE INDEX IF NOT EXISTS lb_receipts_history_idx
    ON public.grocery_receipts(household_id, receipt_date DESC);
CREATE INDEX IF NOT EXISTS lb_pantry_events_history_idx
    ON public.pantry_events(household_id, created_at DESC);
CREATE INDEX IF NOT EXISTS lb_utility_forecasts_history_idx
    ON public.lb_utility_forecasts(household_id, kind, generated_at DESC);
CREATE INDEX IF NOT EXISTS lb_ai_runs_history_idx
    ON public.lb_ai_runs(household_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS lb_ai_recs_run_rank_idx
    ON public.lb_ai_recommendations(run_id, priority_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS lb_activity_history_idx
    ON public.activity_logs(household_id, created_at DESC);

-- RLS: the user's Supabase Auth JWT determines the owner.
CREATE OR REPLACE FUNCTION public.lb_owns_household(p_household_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.households h
        WHERE h.id = p_household_id AND h.owner_id = (SELECT auth.uid())
    );
$$;
REVOKE ALL ON FUNCTION public.lb_owns_household(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.lb_owns_household(uuid) TO authenticated;

ALTER TABLE public.lb_user_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS lb_user_preferences_owner ON public.lb_user_preferences;
CREATE POLICY lb_user_preferences_owner ON public.lb_user_preferences
FOR ALL TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'lb_household_modules', 'lb_assessments', 'lb_utility_profiles',
        'lb_appliances', 'lb_document_reviews', 'lb_utility_forecasts',
        'lb_forecast_checks', 'lb_scenarios', 'lb_ai_runs', 'lb_ai_recommendations'
    ] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS lb_household_owner ON public.%I', t);
        EXECUTE format(
            'CREATE POLICY lb_household_owner ON public.%I FOR ALL TO authenticated '
            || 'USING ((select public.lb_owns_household(household_id))) '
            || 'WITH CHECK ((select public.lb_owns_household(household_id)))', t);
    END LOOP;
END $$;

-- Create permissions for signed-in users only. Existing policies on base tables remain.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.lb_user_preferences,
    public.lb_household_modules,
    public.lb_assessments,
    public.lb_utility_profiles,
    public.lb_appliances,
    public.lb_document_reviews,
    public.lb_utility_forecasts,
    public.lb_forecast_checks,
    public.lb_scenarios,
    public.lb_ai_runs,
    public.lb_ai_recommendations
TO authenticated;

COMMIT;
NOTIFY pgrst, 'reload schema';

-- Read-only quick check; expected output: 11 lb_... tables below, plus 2 from Food.
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN (
    'lb_user_preferences','lb_household_modules','lb_assessments',
    'lb_utility_profiles','lb_appliances','lb_document_reviews',
    'lb_utility_forecasts','lb_forecast_checks','lb_scenarios',
    'lb_ai_runs','lb_ai_recommendations'
) ORDER BY table_name;
