-- LIVEBETTER 06 VERIFICATION (READ ONLY)
-- Replace the email below in BOTH occurrences.
WITH demo AS (
 SELECT h.id AS household_id, h.name FROM public.households h
 JOIN auth.users u ON u.id=h.owner_id
 WHERE lower(u.email)=lower('demo@livebetter.test')
   AND h.name='LiveBetter Full Demo - Seed 06'
), requirements AS (
 SELECT r.id AS recipe_id,r.name, count(i.id) FILTER (WHERE i.optional=false) AS required_count,
        count(i.id) FILTER (WHERE i.optional=false AND p.id IS NOT NULL AND p.available=true AND p.quantity>=i.quantity) AS sufficient_count,
        string_agg(i.ingredient_name || ' (' || i.quantity || ' ' || coalesce(i.unit,'?') || ')',', ' ORDER BY i.ingredient_name)
           FILTER (WHERE i.optional=false AND (p.id IS NULL OR p.available=false OR p.quantity < i.quantity)) AS missing_or_insufficient
 FROM public.lb_recipes r
 JOIN demo d ON r.household_id=d.household_id
 LEFT JOIN public.lb_recipe_ingredients i ON i.recipe_id=r.id
 LEFT JOIN public.pantry_items p
   ON p.household_id=d.household_id AND p.ingredient_name=lower(trim(i.ingredient_name))
   AND p.unit=lower(trim(i.unit))
 GROUP BY r.id,r.name
)
SELECT name,required_count,sufficient_count,
       (required_count>0 AND required_count=sufficient_count) AS cook_now,
       missing_or_insufficient
FROM requirements ORDER BY cook_now DESC,name;

-- Sanity check: cooking recorded once, 4 verified demo bills per utility,
-- two grocery receipts, and all 3 module assessments plus general.
WITH d AS (
 SELECT h.id FROM public.households h JOIN auth.users u ON u.id=h.owner_id
 WHERE lower(u.email)=lower('demo@livebetter.test')
   AND h.name='LiveBetter Full Demo - Seed 06'
)
SELECT 'water bills' AS category,count(*) AS rows_found FROM public.utility_bills
 WHERE household_id IN (SELECT id FROM d) AND kind='water'
UNION ALL SELECT 'electricity bills',count(*) FROM public.utility_bills
 WHERE household_id IN (SELECT id FROM d) AND kind='electricity'
UNION ALL SELECT 'receipts',count(*) FROM public.grocery_receipts
 WHERE household_id IN (SELECT id FROM d)
UNION ALL SELECT 'recipes',count(*) FROM public.lb_recipes
 WHERE household_id IN (SELECT id FROM d)
UNION ALL SELECT 'cooking operations',count(*) FROM public.cooking_operations
 WHERE household_id IN (SELECT id FROM d)
UNION ALL SELECT 'AI runs',count(*) FROM public.lb_ai_runs
 WHERE household_id IN (SELECT id FROM d)
UNION ALL SELECT 'AI recommendations',count(*) FROM public.lb_ai_recommendations
 WHERE household_id IN (SELECT id FROM d)
ORDER BY category;
