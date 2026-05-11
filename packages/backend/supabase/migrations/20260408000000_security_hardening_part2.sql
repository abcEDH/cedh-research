-- Extend security hardening: enable RLS on remaining tables and restrict view access.

-- Tables that previously exposed sensitive data; keep access limited to the service_role.
DO $$
BEGIN
  ALTER TABLE public.regional_elo_game_events ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.regional_elo_state_activity ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.ingestion_backfill_batches ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.ingestion_backfill_runs ENABLE ROW LEVEL SECURITY;
  ALTER TABLE public.ingestion_backfill_events ENABLE ROW LEVEL SECURITY;
EXCEPTION WHEN undefined_table THEN
  RAISE NOTICE 'One or more security tables do not exist yet; skipping enable/rls setup';
END
$$;

-- Service role predicate helper.
CREATE OR REPLACE FUNCTION public.is_service_role() RETURNS boolean AS $$
BEGIN
  RETURN current_setting('request.jwt.claims.role', true) = 'service_role';
END;
$$ LANGUAGE plpgsql STABLE;

-- Policies for tables that should be restricted to service role.
DO $$
DECLARE
  table_name text;
BEGIN
  FOR table_name IN
    SELECT unnest(ARRAY[
      'regional_elo_game_events',
      'ingestion_backfill_batches',
      'ingestion_backfill_runs',
      'ingestion_backfill_events'
    ])
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS "Service role access" ON public.%I', table_name);
    EXECUTE format(
      'CREATE POLICY "Service role access" ON public.%I FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role())',
      table_name
    );
  END LOOP;
END
$$;

-- Policies for regional_elo_state_activity (public read required for leaderboard).
DROP POLICY IF EXISTS "Service role access" ON public.regional_elo_state_activity;
DROP POLICY IF EXISTS "Public read access" ON public.regional_elo_state_activity;

CREATE POLICY "Public read access" ON public.regional_elo_state_activity
  FOR SELECT TO public USING (true);

CREATE POLICY "Service role write access" ON public.regional_elo_state_activity
  FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role());

-- Ensure security_invoker semantics and appropriate grants on views.
DO $$
DECLARE
  view_name text;
  public_views text[] := ARRAY[
    'regional_elo_leaderboard',
    'regional_elo_regions',
    'regional_elo_data_validity',
    'regional_elo_player_stats',
    'regional_elo_primary_state_assignments'
  ];
  private_views text[] := ARRAY[
    'regional_elo_game_event_log'
  ];
BEGIN
  -- Handle public views
  FOREACH view_name IN ARRAY public_views LOOP
    BEGIN
      EXECUTE format('ALTER VIEW public.%I SET (security_invoker = true)', view_name);
      EXECUTE format('GRANT SELECT ON public.%I TO anon, authenticated', view_name);
    EXCEPTION WHEN undefined_table THEN
      RAISE NOTICE 'View % does not exist; skipping', view_name;
    END;
  END LOOP;

  -- Handle private views
  FOREACH view_name IN ARRAY private_views LOOP
    BEGIN
      EXECUTE format('ALTER VIEW public.%I SET (security_invoker = true)', view_name);
      EXECUTE format('REVOKE ALL ON public.%I FROM anon, authenticated', view_name);
      EXECUTE format('GRANT SELECT ON public.%I TO service_role', view_name);
    EXCEPTION WHEN undefined_table THEN
      RAISE NOTICE 'View % does not exist; skipping', view_name;
    END;
  END LOOP;
END
$$;
