-- Compact paginated snapshots for incremental global Elo rebuilds.

CREATE OR REPLACE FUNCTION public.get_global_elo_snapshot_before(
  cutoff timestamptz,
  p_limit integer DEFAULT 1000,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  player_id uuid,
  rating numeric,
  games_played integer,
  wins integer,
  draws integer,
  losses integer,
  last_game_date date
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  WITH latest AS (
    SELECT DISTINCT ON (player_id)
      player_id,
      rating_after
    FROM public.global_elo_game_events
    WHERE region_type = 'global'
      AND region_key = 'ALL'
      AND game_date < cutoff
    ORDER BY player_id, game_date DESC, game_id DESC
  ),
  counts AS (
    SELECT
      player_id,
      count(*)::int AS games_played,
      count(*) FILTER (WHERE game_result = 'win')::int AS wins,
      count(*) FILTER (WHERE game_result = 'draw')::int AS draws,
      count(*) FILTER (WHERE game_result = 'loss')::int AS losses,
      max(game_date)::date AS last_game_date
    FROM public.global_elo_game_events
    WHERE region_type = 'global'
      AND region_key = 'ALL'
      AND game_date < cutoff
    GROUP BY player_id
  )
  SELECT
    counts.player_id,
    latest.rating_after AS rating,
    counts.games_played,
    counts.wins,
    counts.draws,
    counts.losses,
    counts.last_game_date
  FROM counts
  JOIN latest USING (player_id)
  ORDER BY counts.player_id
  LIMIT greatest(0, p_limit)
  OFFSET greatest(0, p_offset);
$$;

CREATE OR REPLACE FUNCTION public.get_global_elo_state_activity_snapshot(
  p_limit integer DEFAULT 1000,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  player_id uuid,
  region_key text,
  country text,
  games_lifetime integer,
  games_30d integer,
  games_90d integer,
  games_365d integer,
  wins integer,
  draws integer,
  losses integer,
  last_game_date date,
  activity_score double precision
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    player_id,
    upper(btrim(state)) AS region_key,
    max(country) FILTER (WHERE country IS NOT NULL AND country <> '') AS country,
    count(*)::int AS games_lifetime,
    count(*) FILTER (WHERE start_date::date >= current_date - interval '30 days')::int AS games_30d,
    count(*) FILTER (WHERE start_date::date >= current_date - interval '90 days')::int AS games_90d,
    count(*) FILTER (WHERE start_date::date >= current_date - interval '365 days')::int AS games_365d,
    count(*) FILTER (WHERE result = 'win')::int AS wins,
    count(*) FILTER (WHERE result = 'draw')::int AS draws,
    count(*) FILTER (WHERE result = 'loss')::int AS losses,
    max(start_date)::date AS last_game_date,
    sum(power(0.5, greatest(0, current_date - start_date::date) / 180.0))::double precision AS activity_score
  FROM public.global_elo_game_results
  WHERE player_id IS NOT NULL
    AND state IS NOT NULL
    AND btrim(state) <> ''
    AND result IN ('win', 'draw', 'loss')
  GROUP BY player_id, upper(btrim(state))
  ORDER BY player_id, upper(btrim(state))
  LIMIT greatest(0, p_limit)
  OFFSET greatest(0, p_offset);
$$;

CREATE OR REPLACE FUNCTION public.get_global_elo_player_meta_snapshot(
  p_limit integer DEFAULT 1000,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  player_id uuid,
  player_name text,
  topdeck_id text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    player_id,
    player_name,
    topdeck_id
  FROM (
    SELECT DISTINCT ON (player_id)
      player_id,
      player_name,
      topdeck_id
    FROM public.global_elo_game_results
    WHERE player_id IS NOT NULL
    ORDER BY player_id, start_date DESC NULLS LAST
  ) meta
  ORDER BY player_id
  LIMIT greatest(0, p_limit)
  OFFSET greatest(0, p_offset);
$$;

REVOKE ALL ON FUNCTION public.get_global_elo_snapshot_before(timestamptz, integer, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_global_elo_state_activity_snapshot(integer, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_global_elo_player_meta_snapshot(integer, integer) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.get_global_elo_snapshot_before(timestamptz, integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_global_elo_state_activity_snapshot(integer, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_global_elo_player_meta_snapshot(integer, integer) TO service_role;
