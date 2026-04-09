-- Use canonical game-event aggregates for leaderboard/profile global counts.
-- The rating table's historical counters can lag behind the event stream.

CREATE OR REPLACE VIEW regional_elo_leaderboard AS
WITH global_counts AS (
  SELECT
    player_id,
    COUNT(*)::integer AS games_played,
    COUNT(*) FILTER (WHERE game_result = 'win')::integer AS wins,
    COUNT(*) FILTER (WHERE game_result = 'draw')::integer AS draws,
    COUNT(*) FILTER (WHERE game_result = 'loss')::integer AS losses,
    MAX(game_date) AS last_game_date
  FROM global_elo_game_events
  WHERE region_type = 'global'
    AND region_key = 'ALL'
  GROUP BY player_id
),
global_rows AS (
  SELECT
    'global'::text AS region_type,
    'ALL'::text AS region_key,
    NULL::text AS country_key,
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    g.rating,
    COALESCE(gc.games_played, 0) AS games_played,
    COALESCE(gc.wins, 0) AS wins,
    COALESCE(gc.draws, 0) AS draws,
    COALESCE(gc.losses, 0) AS losses,
    gc.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      ORDER BY g.rating DESC, COALESCE(gc.games_played, 0) DESC, p.name ASC
    ) AS rank,
    COALESCE(gc.games_played, 0) AS global_games_played,
    COALESCE(gc.wins, 0) AS global_wins,
    COALESCE(gc.draws, 0) AS global_draws,
    COALESCE(gc.losses, 0) AS global_losses,
    NULL::numeric AS activity_score,
    NULL::integer AS games_30d,
    NULL::integer AS games_90d,
    NULL::integer AS games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM global_elo_ratings g
  JOIN players p ON p.id = g.player_id
  LEFT JOIN global_counts gc ON gc.player_id = g.player_id
  LEFT JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
),
country_rows AS (
  SELECT
    'country'::text AS region_type,
    s.country_key AS region_key,
    s.country_key,
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    g.rating,
    COALESCE(gc.games_played, 0) AS games_played,
    COALESCE(gc.wins, 0) AS wins,
    COALESCE(gc.draws, 0) AS draws,
    COALESCE(gc.losses, 0) AS losses,
    gc.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.country_key
      ORDER BY g.rating DESC, s.activity_score DESC, s.games_played DESC, p.name ASC
    ) AS rank,
    COALESCE(gc.games_played, 0) AS global_games_played,
    COALESCE(gc.wins, 0) AS global_wins,
    COALESCE(gc.draws, 0) AS global_draws,
    COALESCE(gc.losses, 0) AS global_losses,
    s.activity_score,
    s.games_30d,
    s.games_90d,
    s.games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM global_elo_ratings g
  JOIN players p ON p.id = g.player_id
  JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  LEFT JOIN global_counts gc ON gc.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
    AND s.country_key IS NOT NULL
    AND s.country_key <> ''
),
state_rows AS (
  SELECT
    'state'::text AS region_type,
    s.region_key,
    s.country_key,
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    g.rating,
    COALESCE(gc.games_played, 0) AS games_played,
    COALESCE(gc.wins, 0) AS wins,
    COALESCE(gc.draws, 0) AS draws,
    COALESCE(gc.losses, 0) AS losses,
    gc.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.country_key, s.region_key
      ORDER BY g.rating DESC, s.activity_score DESC, s.games_played DESC, p.name ASC
    ) AS rank,
    COALESCE(gc.games_played, 0) AS global_games_played,
    COALESCE(gc.wins, 0) AS global_wins,
    COALESCE(gc.draws, 0) AS global_draws,
    COALESCE(gc.losses, 0) AS global_losses,
    s.activity_score,
    s.games_30d,
    s.games_90d,
    s.games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM global_elo_ratings g
  JOIN players p ON p.id = g.player_id
  JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  LEFT JOIN global_counts gc ON gc.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
)
SELECT * FROM global_rows
UNION ALL
SELECT * FROM country_rows
UNION ALL
SELECT * FROM state_rows;

CREATE OR REPLACE VIEW global_elo_leaderboard AS
SELECT * FROM regional_elo_leaderboard;

ALTER VIEW regional_elo_leaderboard SET (security_invoker = true);
ALTER VIEW global_elo_leaderboard SET (security_invoker = true);

GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
GRANT SELECT ON global_elo_leaderboard TO anon, authenticated;
