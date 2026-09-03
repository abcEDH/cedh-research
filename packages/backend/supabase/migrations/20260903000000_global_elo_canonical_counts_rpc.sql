-- Read canonical global game-event counts without evaluating the much wider
-- regional_elo_leaderboard view. Keyset pagination keeps each request bounded
-- while preserving the view's event-derived count semantics.

CREATE OR REPLACE FUNCTION public.get_global_elo_canonical_counts(
  p_after_player_id uuid DEFAULT NULL,
  p_limit integer DEFAULT 1000
)
RETURNS TABLE (
  player_id uuid,
  games_played integer,
  wins integer,
  losses integer,
  draws integer,
  last_game_date date
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    e.player_id,
    count(*)::integer AS games_played,
    count(*) FILTER (WHERE e.game_result = 'win')::integer AS wins,
    count(*) FILTER (WHERE e.game_result = 'loss')::integer AS losses,
    count(*) FILTER (WHERE e.game_result = 'draw')::integer AS draws,
    max(e.game_date)::date AS last_game_date
  FROM public.global_elo_game_events e
  WHERE e.region_type = 'global'
    AND e.region_key = 'ALL'
    AND (p_after_player_id IS NULL OR e.player_id > p_after_player_id)
  GROUP BY e.player_id
  ORDER BY e.player_id
  LIMIT greatest(0, p_limit);
$$;

REVOKE ALL ON FUNCTION public.get_global_elo_canonical_counts(uuid, integer)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_global_elo_canonical_counts(uuid, integer)
  TO service_role;
