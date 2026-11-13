-- LiveBetter surprise card (misuse): per-user security record.
-- Run once in the Supabase SQL Editor AFTER 01, 02 and 03. Safe to run again; changes no existing table.
--
-- One JSON document per user: pattern hash (PBKDF2, salted), authenticator secret (Fernet-encrypted with the
-- backend's MFA_ENCRYPTION_KEY, so the database alone cannot produce codes), hashed recovery codes,
-- failed-attempt counters and lockouts, one-time pattern permissions, recent security events and the
-- 24-hour reset snapshot. Nothing in it is readable as a secret.
--
-- Known limit (hackathon scope): with this RLS policy a signed-in user could edit their own row directly
-- through the Supabase API, e.g. clear their own lockout. That needs the owner's own login, so it does not
-- help the misuser in our scenario (someone using the owner's unlocked phone through the app). A production
-- version would allow only a backend service role or SECURITY DEFINER functions to write this table.
BEGIN;

CREATE TABLE IF NOT EXISTS public.user_security (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  data jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_security ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users access own security record" ON public.user_security;
CREATE POLICY "Users access own security record" ON public.user_security
  FOR ALL TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

GRANT SELECT, INSERT, UPDATE ON public.user_security TO authenticated;

COMMIT;
NOTIFY pgrst, 'reload schema';
