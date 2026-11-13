-- Optional recommended final step AFTER 03_livebetter_integration_extension.sql.
-- Atomically stores a complete Big Brain run + actions + activity event.
-- Call with a STABLE p_run_id UUID on retries. Requires a Supabase user JWT.
BEGIN;
CREATE OR REPLACE FUNCTION public.lb_save_ai_run(
    p_run_id uuid,
    p_household_id uuid,
    p_status text,
    p_model_name text,
    p_module_status jsonb,
    p_module_summaries jsonb,
    p_decision_context jsonb,
    p_dashboard jsonb,
    p_actions jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    v_inserted uuid;
    v_existing_household uuid;
    v_action jsonb;
BEGIN
    IF p_run_id IS NULL OR p_household_id IS NULL
        OR NOT (SELECT public.lb_owns_household(p_household_id)) THEN
        RAISE EXCEPTION 'Unauthorized household' USING ERRCODE = '42501';
    END IF;

    IF p_status NOT IN ('success', 'partial', 'failed')
        OR p_status IS NULL
        OR p_actions IS NULL OR jsonb_typeof(p_actions) <> 'array'
        OR p_dashboard IS NULL OR jsonb_typeof(p_dashboard) <> 'object'
        OR p_module_status IS NULL OR jsonb_typeof(p_module_status) <> 'object'
        OR p_module_summaries IS NULL OR jsonb_typeof(p_module_summaries) <> 'object'
        OR p_decision_context IS NULL OR jsonb_typeof(p_decision_context) <> 'object' THEN
        RAISE EXCEPTION 'Invalid run payload' USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.lb_ai_runs (
        id, household_id, status, model_name, module_status,
        module_summaries, decision_context, dashboard
    ) VALUES (
        p_run_id, p_household_id, p_status, p_model_name, p_module_status,
        p_module_summaries, p_decision_context, p_dashboard
    ) ON CONFLICT (id) DO NOTHING RETURNING id INTO v_inserted;

    IF v_inserted IS NULL THEN
        SELECT household_id INTO v_existing_household
        FROM public.lb_ai_runs WHERE id = p_run_id;
        IF v_existing_household IS DISTINCT FROM p_household_id THEN
            RAISE EXCEPTION 'Run ID belongs to another household' USING ERRCODE = '42501';
        END IF;
        -- This operation ID already committed successfully on an earlier call.
        RETURN p_run_id;
    END IF;

    FOR v_action IN SELECT value FROM jsonb_array_elements(p_actions) LOOP
        IF jsonb_typeof(v_action) <> 'object' THEN
            RAISE EXCEPTION 'Invalid action object' USING ERRCODE = '22023';
        END IF;

        INSERT INTO public.lb_ai_recommendations (
            run_id, household_id, source, module, action_id,
            title, estimated_savings_mur, confidence, evidence, assumptions,
            period_start, period_end, priority_score, explanation
        ) VALUES (
            p_run_id,
            p_household_id,
            v_action->>'source',
            v_action->>'module',
            v_action->>'action_id',
            v_action->>'title',
            NULLIF(v_action->>'estimated_savings_mur','')::numeric,
            NULLIF(v_action->>'confidence',''),
            COALESCE(v_action->'evidence', '{}'::jsonb),
            COALESCE(v_action->'assumptions', '{}'::jsonb),
            NULLIF(v_action->>'period_start','')::date,
            NULLIF(v_action->>'period_end','')::date,
            NULLIF(v_action->>'priority_score','')::numeric,
            v_action->>'explanation'
        );
    END LOOP;

    INSERT INTO public.activity_logs (household_id, event_type, related_entity_id, details)
    VALUES (
        p_household_id, 'insights_generated', p_run_id,
        jsonb_build_object('action_count', jsonb_array_length(p_actions), 'status', p_status)
    );

    RETURN p_run_id;
END;
$$;

REVOKE ALL ON FUNCTION public.lb_save_ai_run(
    uuid, uuid, text, text, jsonb, jsonb, jsonb, jsonb, jsonb
) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.lb_save_ai_run(
    uuid, uuid, text, text, jsonb, jsonb, jsonb, jsonb, jsonb
) TO authenticated;
COMMIT;
NOTIFY pgrst, 'reload schema';
