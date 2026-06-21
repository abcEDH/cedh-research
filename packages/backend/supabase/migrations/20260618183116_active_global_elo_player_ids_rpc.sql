-- Distinct active global Elo player ids since a cutoff.
--
-- Replaces the previous client-side approach where detect_active_players paged
-- every matching global_elo_game_results row (200k+) through PostgREST with
-- OFFSET and deduped in Python. Deep OFFSET scans tripped the Postgres
-- statement_timeout (57014). DISTINCT in SQL returns only the active players
-- (a few thousand) and lets the planner use the start_date index.

CREATE OR REPLACE FUNCTION public.get_active_global_elo_player_ids(
  cutoff date,
  p_limit integer DEFAULT 1000,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  player_id uuid
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT DISTINCT player_id
  FROM public.global_elo_game_results
  WHERE player_id IS NOT NULL
    AND start_date >= cutoff
    AND result <> 'bye'
  ORDER BY player_id
  LIMIT greatest(0, p_limit)
  OFFSET greatest(0, p_offset);
$$;

REVOKE ALL ON FUNCTION public.get_active_global_elo_player_ids(date, integer, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_active_global_elo_player_ids(date, integer, integer) TO service_role;
