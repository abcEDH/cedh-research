-- Follow up security hardening for objects recreated or renamed after the
-- initial advisor cleanup.

-- Pin explicit search_path values for functions created after the blanket
-- hardening migration so later CREATE OR REPLACE statements do not regress.
ALTER FUNCTION public.compute_game_key(uuid, integer, text, integer, boolean)
  SET search_path = public, extensions;

ALTER FUNCTION public.set_canonical_game_key()
  SET search_path = public, extensions;

-- Ensure recreated public views run with caller privileges instead of owner
-- privileges.
ALTER VIEW public.regional_elo_data_validity SET (security_invoker = true);
ALTER VIEW public.player_commander_entries SET (security_invoker = true);
ALTER VIEW public.regional_elo_game_event_log SET (security_invoker = true);

-- Enable RLS on currently-active public tables exposed through PostgREST.
ALTER TABLE public.ingestion_backfill_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_backfill_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingestion_backfill_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.global_elo_game_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.global_elo_state_activity ENABLE ROW LEVEL SECURITY;

-- Service-role-only backfill telemetry access.
DO $$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY[
    'ingestion_backfill_batches',
    'ingestion_backfill_runs',
    'ingestion_backfill_events'
  ]
  LOOP
    EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated', table_name);
    EXECUTE format('DROP POLICY IF EXISTS "Service role access" ON public.%I', table_name);
    EXECUTE format(
      'CREATE POLICY "Service role access" ON public.%I FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role())',
      table_name
    );
  END LOOP;
END
$$;

DROP POLICY IF EXISTS "Public read access" ON public.global_elo_game_events;
DROP POLICY IF EXISTS "Service role write access" ON public.global_elo_game_events;
DROP POLICY IF EXISTS "Service role access" ON public.global_elo_game_events;

CREATE POLICY "Public read access" ON public.global_elo_game_events
  FOR SELECT TO public
  USING (region_type = 'global' AND region_key = 'ALL');

CREATE POLICY "Service role write access" ON public.global_elo_game_events
  FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role());

-- Keep public read access on state activity because the leaderboard and
-- profile views depend on it under security_invoker semantics.
DROP POLICY IF EXISTS "Public read access" ON public.global_elo_state_activity;
DROP POLICY IF EXISTS "Service role write access" ON public.global_elo_state_activity;
DROP POLICY IF EXISTS "Service role access" ON public.global_elo_state_activity;

CREATE POLICY "Public read access" ON public.global_elo_state_activity
  FOR SELECT TO public USING (true);

CREATE POLICY "Service role write access" ON public.global_elo_state_activity
  FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role());
