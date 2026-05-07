-- Include tournaments without state metadata in global Elo while keeping region filters assignment-based.

CREATE OR REPLACE VIEW regional_elo_game_results AS
SELECT
  g.id AS game_id,
  g.tournament_id,
  t.start_date,
  t.state,
  t.country,
  t.city,
  t.name AS tournament_name,
  gp.entry_id,
  te.player_id,
  p.topdeck_id,
  p.name AS player_name,
  gp.result,
  g.is_draw,
  g.round_number,
  g.round_name,
  g.table_number
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
JOIN tournaments t ON g.tournament_id = t.id;

CREATE OR REPLACE VIEW regional_elo_leaderboard AS
WITH global_rows AS (
  SELECT
    'global'::text AS region_type,
    'ALL'::text AS region_key,
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
    s.region_key AS primary_region_key,
    s.country_key AS primary_country_key,
    NULL::text AS country_key
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
    s.region_key AS primary_region_key,
    s.country_key AS primary_country_key,
    s.country_key AS country_key
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
    s.region_key AS primary_region_key,
    s.country_key AS primary_country_key,
    s.country_key AS country_key
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

ALTER VIEW regional_elo_game_results SET (security_invoker = true);
ALTER VIEW regional_elo_leaderboard SET (security_invoker = true);

GRANT SELECT ON regional_elo_game_results TO anon, authenticated;
GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
