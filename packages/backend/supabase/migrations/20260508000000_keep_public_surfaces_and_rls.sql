-- Keep the public API surface public while satisfying Supabase security lints.

-- player_commander_entries should be a security_invoker view, but it still needs
-- direct read access to its base tables for anon/authenticated callers.
ALTER VIEW player_commander_entries SET (security_invoker = true);

GRANT SELECT ON TABLE
  public.players,
  public.tournament_entries,
  public.commanders,
  public.tournaments
TO anon, authenticated;

GRANT SELECT ON player_commander_entries TO anon, authenticated;

-- The public Elo tables are meant to remain readable, so enable RLS and add
-- explicit public-read policies plus service-role write access.
ALTER TABLE public.global_elo_state_activity ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access" ON public.global_elo_state_activity;
DROP POLICY IF EXISTS "Service role write access" ON public.global_elo_state_activity;
CREATE POLICY "Public read access" ON public.global_elo_state_activity
  FOR SELECT TO public USING (true);
CREATE POLICY "Service role write access" ON public.global_elo_state_activity
  FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role());

ALTER TABLE public.global_elo_game_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access" ON public.global_elo_game_events;
DROP POLICY IF EXISTS "Service role write access" ON public.global_elo_game_events;
CREATE POLICY "Public read access" ON public.global_elo_game_events
  FOR SELECT TO public USING (true);
CREATE POLICY "Service role write access" ON public.global_elo_game_events
  FOR ALL TO public USING (public.is_service_role()) WITH CHECK (public.is_service_role());
