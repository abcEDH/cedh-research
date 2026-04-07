-- Add country-level Regional Elo slices derived from primary state assignments.

ALTER TABLE regional_elo_state_activity
  ADD COLUMN IF NOT EXISTS country_key text;

CREATE INDEX IF NOT EXISTS regional_elo_state_activity_country_idx
  ON regional_elo_state_activity (country_key, region_key, is_primary_state, activity_score DESC);

CREATE OR REPLACE VIEW regional_elo_primary_state_assignments AS
SELECT
  a.region_type,
  a.region_key,
  a.country_key,
  a.player_id,
  a.games_30d,
  a.games_90d,
  a.games_365d,
  a.games_lifetime,
  a.wins,
  a.draws,
  a.losses,
  a.last_game_date,
  a.activity_score,
  a.updated_at
FROM regional_elo_state_activity a
WHERE a.region_type = 'state'
  AND a.is_primary_state = true;

CREATE OR REPLACE VIEW regional_elo_player_stats AS
SELECT
  region_type,
  region_key,
  country_key,
  player_id,
  games_lifetime AS games_played,
  wins,
  draws,
  losses,
  last_game_date,
  activity_score,
  games_30d,
  games_90d,
  games_365d
FROM regional_elo_primary_state_assignments;

CREATE OR REPLACE VIEW regional_elo_leaderboard AS
WITH global_rows AS (
  SELECT
    'global'::text AS region_type,
    'ALL'::text AS region_key,
    NULL::text AS country_key,
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    g.rating,
    g.games_played,
    g.wins,
    g.draws,
    g.losses,
    g.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      ORDER BY g.rating DESC, g.games_played DESC, p.name ASC
    ) AS rank,
    g.games_played AS global_games_played,
    g.wins AS global_wins,
    g.draws AS global_draws,
    g.losses AS global_losses,
    NULL::numeric AS activity_score,
    NULL::integer AS games_30d,
    NULL::integer AS games_90d,
    NULL::integer AS games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM regional_elo_ratings g
  JOIN players p ON p.id = g.player_id
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
    s.games_played,
    s.wins,
    s.draws,
    s.losses,
    s.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.country_key
      ORDER BY g.rating DESC, s.activity_score DESC, s.games_played DESC, p.name ASC
    ) AS rank,
    g.games_played AS global_games_played,
    g.wins AS global_wins,
    g.draws AS global_draws,
    g.losses AS global_losses,
    s.activity_score,
    s.games_30d,
    s.games_90d,
    s.games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM regional_elo_ratings g
  JOIN players p ON p.id = g.player_id
  JOIN regional_elo_player_stats s ON s.player_id = g.player_id
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
    s.games_played,
    s.wins,
    s.draws,
    s.losses,
    s.last_game_date,
    g.updated_at,
    ROW_NUMBER() OVER (
      PARTITION BY s.country_key, s.region_key
      ORDER BY g.rating DESC, s.activity_score DESC, s.games_played DESC, p.name ASC
    ) AS rank,
    g.games_played AS global_games_played,
    g.wins AS global_wins,
    g.draws AS global_draws,
    g.losses AS global_losses,
    s.activity_score,
    s.games_30d,
    s.games_90d,
    s.games_365d,
    s.country_key AS primary_country_key,
    s.region_key AS primary_region_key
  FROM regional_elo_ratings g
  JOIN players p ON p.id = g.player_id
  JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
)
SELECT * FROM global_rows
UNION ALL
SELECT * FROM country_rows
UNION ALL
SELECT * FROM state_rows;

CREATE OR REPLACE VIEW regional_elo_regions AS
WITH global_region AS (
  SELECT
    'global'::text AS region_type,
    'ALL'::text AS region_key,
    NULL::text AS country_key,
    COUNT(*)::bigint AS player_count,
    MAX(updated_at) AS updated_at
  FROM regional_elo_ratings
  WHERE region_type = 'global'
    AND region_key = 'ALL'
),
country_regions AS (
  SELECT
    'country'::text AS region_type,
    country_key AS region_key,
    country_key,
    COUNT(*)::bigint AS player_count,
    MAX(updated_at) AS updated_at
  FROM regional_elo_primary_state_assignments
  WHERE country_key IS NOT NULL
    AND country_key <> ''
  GROUP BY country_key
),
state_regions AS (
  SELECT
    region_type,
    region_key,
    country_key,
    COUNT(*)::bigint AS player_count,
    MAX(updated_at) AS updated_at
  FROM regional_elo_primary_state_assignments
  GROUP BY region_type, region_key, country_key
)
SELECT * FROM global_region
UNION ALL
SELECT * FROM country_regions
UNION ALL
SELECT * FROM state_regions;

ALTER VIEW regional_elo_primary_state_assignments SET (security_invoker = true);
ALTER VIEW regional_elo_player_stats SET (security_invoker = true);
ALTER VIEW regional_elo_leaderboard SET (security_invoker = true);
ALTER VIEW regional_elo_regions SET (security_invoker = true);

GRANT SELECT ON regional_elo_primary_state_assignments TO anon, authenticated;
GRANT SELECT ON regional_elo_player_stats TO anon, authenticated;
GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
GRANT SELECT ON regional_elo_regions TO anon, authenticated;
