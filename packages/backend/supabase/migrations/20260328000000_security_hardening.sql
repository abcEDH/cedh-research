-- Security hardening for Supabase advisor findings
-- 1. Enable RLS on public.regional_elo_ratings
-- 2. Convert public views to SECURITY INVOKER semantics
-- 3. Pin public function search_path to avoid mutable search path warnings

ALTER TABLE public.regional_elo_ratings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON public.regional_elo_ratings;
CREATE POLICY "Public read access"
ON public.regional_elo_ratings
FOR SELECT
USING (true);

DO $$
DECLARE
  view_name text;
BEGIN
  FOR view_name IN
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'v'
  LOOP
    EXECUTE format(
      'ALTER VIEW public.%I SET (security_invoker = true)',
      view_name
    );
  END LOOP;
END
$$;

DO $$
DECLARE
  fn record;
BEGIN
  FOR fn IN
    SELECT
      p.proname,
      pg_get_function_identity_arguments(p.oid) AS identity_args
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.prokind = 'f'
  LOOP
    EXECUTE format(
      'ALTER FUNCTION public.%I(%s) SET search_path = public, extensions',
      fn.proname,
      fn.identity_args
    );
  END LOOP;
END
$$;
