-- Canonical regional stats derived from the same included-game source
-- used by the Elo pipeline. This keeps leaderboard summaries aligned
-- with reconstructible player drilldowns even if rating rows are stale.

CREATE OR REPLACE VIEW regional_elo_player_stats AS
WITH canonical_results AS (
  SELECT
    'state'::text AS region_type,
    upper(trim(state)) AS region_key,
    player_id,
    result,
    start_date::date AS game_date
  FROM regional_elo_game_results
  WHERE state IS NOT NULL
    AND trim(state) <> ''
    AND result <> 'bye'
)
SELECT
  region_type,
  region_key,
  player_id,
  COUNT(*)::integer AS games_played,
  COUNT(*) FILTER (WHERE result = 'win')::integer AS wins,
  COUNT(*) FILTER (WHERE result = 'draw')::integer AS draws,
  COUNT(*) FILTER (WHERE result = 'loss')::integer AS losses,
  MAX(game_date) AS last_game_date
FROM canonical_results
GROUP BY region_type, region_key, player_id;

CREATE OR REPLACE VIEW regional_elo_leaderboard AS
SELECT
  r.region_type,
  r.region_key,
  r.player_id,
  p.name AS player_name,
  p.topdeck_id,
  r.rating,
  COALESCE(s.games_played, 0) AS games_played,
  COALESCE(s.wins, 0) AS wins,
  COALESCE(s.draws, 0) AS draws,
  COALESCE(s.losses, 0) AS losses,
  s.last_game_date,
  r.updated_at,
  ROW_NUMBER() OVER (
    PARTITION BY r.region_type, r.region_key
    ORDER BY r.rating DESC, COALESCE(s.games_played, 0) DESC
  ) AS rank
FROM regional_elo_ratings r
JOIN players p ON p.id = r.player_id
LEFT JOIN regional_elo_player_stats s
  ON s.region_type = r.region_type
 AND s.region_key = r.region_key
 AND s.player_id = r.player_id;

GRANT SELECT ON regional_elo_player_stats TO anon, authenticated;
GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
