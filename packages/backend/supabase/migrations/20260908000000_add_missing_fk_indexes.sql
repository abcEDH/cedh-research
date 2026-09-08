-- Add indexes for foreign-key columns flagged by Supabase performance advisors.
-- These support joins, parent-row cleanup, and Elo maintenance writes.

CREATE INDEX IF NOT EXISTS commander_matchups_game_id_idx
  ON public.commander_matchups (game_id);

CREATE INDEX IF NOT EXISTS commander_matchups_tournament_id_idx
  ON public.commander_matchups (tournament_id);

CREATE INDEX IF NOT EXISTS global_elo_game_events_game_id_idx
  ON public.global_elo_game_events (game_id);

CREATE INDEX IF NOT EXISTS global_elo_game_events_tournament_id_idx
  ON public.global_elo_game_events (tournament_id);

CREATE INDEX IF NOT EXISTS global_elo_game_events_entry_id_idx
  ON public.global_elo_game_events (entry_id);

CREATE INDEX IF NOT EXISTS global_elo_ratings_player_id_idx
  ON public.global_elo_ratings (player_id);

-- Snapshot and canonical-count RPCs always filter on the global region and then
-- group/order by player and game date. This avoids a large incremental sort.
CREATE INDEX IF NOT EXISTS global_elo_game_events_snapshot_idx
  ON public.global_elo_game_events
    (region_type, region_key, player_id, game_date DESC, game_id DESC);

-- Evaluate request-role checks once per statement instead of once per row.
-- The predicates are semantically unchanged.
ALTER POLICY "Service role full access" ON public.elo_maintenance_jobs
  TO service_role
  USING ((SELECT auth.role()) = 'service_role')
  WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access" ON public.ingestion_jobs
  TO service_role
  USING ((SELECT auth.role()) = 'service_role')
  WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role full access" ON public.partner_commander_sweep_state
  TO service_role
  USING ((SELECT auth.role()) = 'service_role')
  WITH CHECK ((SELECT auth.role()) = 'service_role');

ALTER POLICY "Service role write access" ON public.global_elo_game_events
  TO service_role
  USING ((SELECT public.is_service_role()))
  WITH CHECK ((SELECT public.is_service_role()));

ALTER POLICY "Service role write access" ON public.global_elo_state_activity
  TO service_role
  USING ((SELECT public.is_service_role()))
  WITH CHECK ((SELECT public.is_service_role()));
