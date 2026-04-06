-- Shift from per-state Elo pools to a single global Elo plus derived state activity.

CREATE TABLE IF NOT EXISTS regional_elo_state_activity (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  region_type text NOT NULL,
  region_key text NOT NULL,
  player_id uuid NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  games_30d integer NOT NULL DEFAULT 0,
  games_90d integer NOT NULL DEFAULT 0,
  games_365d integer NOT NULL DEFAULT 0,
  games_lifetime integer NOT NULL DEFAULT 0,
  wins integer NOT NULL DEFAULT 0,
  draws integer NOT NULL DEFAULT 0,
  losses integer NOT NULL DEFAULT 0,
  last_game_date date,
  activity_score numeric NOT NULL DEFAULT 0,
  is_primary_state boolean NOT NULL DEFAULT false,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (region_type, region_key, player_id)
);

CREATE INDEX IF NOT EXISTS regional_elo_state_activity_region_idx
  ON regional_elo_state_activity (region_type, region_key, is_primary_state, activity_score DESC);

CREATE INDEX IF NOT EXISTS regional_elo_state_activity_player_idx
  ON regional_elo_state_activity (player_id, is_primary_state, activity_score DESC);

CREATE OR REPLACE VIEW regional_elo_primary_state_assignments AS
SELECT
  a.region_type,
  a.region_key,
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
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    s.region_key AS primary_region_key,
    g.rating,
    g.games_played,
    g.wins,
    g.draws,
    g.losses,
    g.last_game_date,
    g.updated_at,
    g.games_played AS global_games_played,
    g.wins AS global_wins,
    g.draws AS global_draws,
    g.losses AS global_losses,
    NULL::numeric AS activity_score,
    NULL::integer AS games_30d,
    NULL::integer AS games_90d,
    NULL::integer AS games_365d,
    ROW_NUMBER() OVER (
      ORDER BY g.rating DESC, g.games_played DESC, p.name ASC
    ) AS rank
  FROM regional_elo_ratings g
  JOIN players p ON p.id = g.player_id
  LEFT JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
),
state_rows AS (
  SELECT
    'state'::text AS region_type,
    s.region_key,
    g.player_id,
    p.name AS player_name,
    p.topdeck_id,
    s.region_key AS primary_region_key,
    g.rating,
    s.games_played,
    s.wins,
    s.draws,
    s.losses,
    s.last_game_date,
    g.updated_at,
    g.games_played AS global_games_played,
    g.wins AS global_wins,
    g.draws AS global_draws,
    g.losses AS global_losses,
    s.activity_score,
    s.games_30d,
    s.games_90d,
    s.games_365d,
    ROW_NUMBER() OVER (
      PARTITION BY s.region_key
      ORDER BY g.rating DESC, s.activity_score DESC, s.games_played DESC, p.name ASC
    ) AS rank
  FROM regional_elo_ratings g
  JOIN players p ON p.id = g.player_id
  JOIN regional_elo_player_stats s ON s.player_id = g.player_id
  WHERE g.region_type = 'global'
    AND g.region_key = 'ALL'
)
SELECT * FROM global_rows
UNION ALL
SELECT * FROM state_rows;

CREATE OR REPLACE VIEW regional_elo_regions AS
WITH global_region AS (
  SELECT
    'global'::text AS region_type,
    'ALL'::text AS region_key,
    COUNT(*)::bigint AS player_count,
    MAX(updated_at) AS updated_at
  FROM regional_elo_ratings
  WHERE region_type = 'global'
    AND region_key = 'ALL'
),
state_regions AS (
  SELECT
    region_type,
    region_key,
    COUNT(*)::bigint AS player_count,
    MAX(updated_at) AS updated_at
  FROM regional_elo_primary_state_assignments
  GROUP BY region_type, region_key
)
SELECT * FROM global_region
UNION ALL
SELECT * FROM state_regions;

CREATE OR REPLACE VIEW regional_elo_game_event_log AS
SELECT
  e.region_type,
  e.region_key,
  e.game_id,
  e.tournament_id,
  e.player_id,
  p.name AS player_name,
  p.topdeck_id,
  e.entry_id,
  e.game_date,
  t.name AS tournament_name,
  t.state,
  g.round_number,
  g.round_name,
  g.table_number,
  gp.seat_position,
  c.name AS commander_name,
  e.game_result,
  e.is_draw,
  e.opponent_count,
  e.expected_score,
  e.actual_score,
  e.rating_before,
  e.rating_delta,
  e.rating_after
FROM regional_elo_game_events e
JOIN players p ON p.id = e.player_id
JOIN tournament_entries te ON te.id = e.entry_id
LEFT JOIN commanders c ON c.id = te.commander_id
JOIN tournaments t ON t.id = e.tournament_id
JOIN games g ON g.id = e.game_id
JOIN game_participants gp ON gp.game_id = e.game_id AND gp.entry_id = e.entry_id
WHERE e.region_type = 'global'
  AND e.region_key = 'ALL';

GRANT SELECT ON regional_elo_state_activity TO anon, authenticated;
GRANT SELECT ON regional_elo_primary_state_assignments TO anon, authenticated;
GRANT SELECT ON regional_elo_player_stats TO anon, authenticated;
GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
GRANT SELECT ON regional_elo_regions TO anon, authenticated;
GRANT SELECT ON regional_elo_game_event_log TO anon, authenticated;
