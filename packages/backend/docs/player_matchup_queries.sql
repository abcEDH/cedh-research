-- SQL Queries for Player Matchup Analysis
-- Run these against Supabase directly or consume the JSON API export
--
-- Tier-aware exports should source game rows from one of these views:
--   games_ranking_eligible, games_local_eligible, games_all_eligible
-- or filter games_elo_tiers with: WHERE elo_tier = 'ranking'

-- ==============================================================================
-- Query 1: Get a specific player's match history by opponent
-- ==============================================================================
-- Replace 'Jason Doan // CriticalEDH' with any player name
WITH player_data AS (
  SELECT id, name, topdeck_id
  FROM players
  WHERE name = 'Jason Doan // CriticalEDH'
),
player_entries AS (
  SELECT id, player_id
  FROM tournament_entries
  WHERE player_id = (SELECT id FROM player_data)
),
player_games AS (
  SELECT
    gp.game_id,
    gp.entry_id,
    gp.result,
    g.tournament_id
  FROM game_participants gp
  JOIN games g ON g.id = gp.game_id
  WHERE gp.entry_id IN (SELECT id FROM player_entries)
),
opponent_data AS (
  SELECT
    gp2.game_id,
    gp2.entry_id,
    te.player_id,
    p.name AS opponent_name,
    p.topdeck_id
  FROM game_participants gp2
  JOIN tournament_entries te ON te.id = gp2.entry_id
  JOIN players p ON p.id = te.player_id
  WHERE gp2.game_id IN (SELECT game_id FROM player_games)
    AND gp2.entry_id NOT IN (SELECT id FROM player_entries)
)
SELECT
  pg.game_id,
  g.tournament_id,
  t.name AS tournament_name,
  t.start_date,
  (SELECT name FROM player_data) AS player_name,
  pg.result AS player_result,
  od.opponent_name,
  od.topdeck_id AS opponent_topdeck_id,
  COALESCE(COUNT(*) FILTER (WHERE od.opponent_name = od.opponent_name AND pg.result = 'win'), 0)
    OVER (PARTITION BY od.opponent_name) AS wins_vs_opponent,
  COALESCE(COUNT(*) FILTER (WHERE od.opponent_name = od.opponent_name AND pg.result = 'loss'), 0)
    OVER (PARTITION BY od.opponent_name) AS losses_vs_opponent,
  COALESCE(COUNT(*) FILTER (WHERE od.opponent_name = od.opponent_name AND pg.result = 'draw'), 0)
    OVER (PARTITION BY od.opponent_name) AS draws_vs_opponent
FROM player_games pg
JOIN games g ON g.id = pg.game_id
JOIN tournaments t ON t.id = g.tournament_id
JOIN opponent_data od ON od.game_id = pg.game_id
ORDER BY t.start_date DESC, pg.game_id;

-- ==============================================================================
-- Query 2: Matchup Summary (aggregated wins/losses by opponent)
-- ==============================================================================
-- Simpler version for just the summary stats
WITH player_data AS (
  SELECT id, name, topdeck_id
  FROM players
  WHERE name = 'Jason Doan // CriticalEDH'
),
player_entries AS (
  SELECT id
  FROM tournament_entries
  WHERE player_id = (SELECT id FROM player_data)
),
game_results AS (
  SELECT
    gp1.result,
    p2.name AS opponent_name,
    p2.topdeck_id,
    gp1.game_id
  FROM game_participants gp1
  JOIN tournament_entries te1 ON te1.id = gp1.entry_id
  JOIN game_participants gp2 ON gp2.game_id = gp1.game_id AND gp2.entry_id != gp1.entry_id
  JOIN tournament_entries te2 ON te2.id = gp2.entry_id
  JOIN players p2 ON p2.id = te2.player_id
  WHERE te1.player_id = (SELECT id FROM player_data)
)
SELECT
  opponent_name,
  topdeck_id,
  COUNT(*) as total_games,
  COUNT(*) FILTER (WHERE result = 'win') as wins,
  COUNT(*) FILTER (WHERE result = 'loss') as losses,
  COUNT(*) FILTER (WHERE result = 'draw') as draws,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE result = 'win') / COUNT(*),
    1
  ) as win_pct
FROM game_results
GROUP BY opponent_name, topdeck_id
ORDER BY total_games DESC;

-- ==============================================================================
-- Query 3: All Player Matchups (for everyone) - BIG EXPORT
-- ==============================================================================
WITH all_game_results AS (
  SELECT
    p1.name AS player_name,
    p1.topdeck_id,
    p2.name AS opponent_name,
    p2.topdeck_id AS opponent_topdeck_id,
    gp1.result,
    t.name AS tournament_name,
    t.start_date,
    g.round_number
  FROM game_participants gp1
  JOIN game_participants gp2 ON gp2.game_id = gp1.game_id
    AND gp2.entry_id != gp1.entry_id
  JOIN tournament_entries te1 ON te1.id = gp1.entry_id
  JOIN tournament_entries te2 ON te2.id = gp2.entry_id
  JOIN players p1 ON p1.id = te1.player_id
  JOIN players p2 ON p2.id = te2.player_id
  JOIN games g ON g.id = gp1.game_id
  JOIN tournaments t ON t.id = g.tournament_id
)
SELECT *
FROM all_game_results
ORDER BY player_name, start_date DESC;

-- ==============================================================================
-- Query 4: Player Win Rate by Opponent (Top 100 matchups)
-- ==============================================================================
WITH game_results AS (
  SELECT
    p1.name AS player_name,
    p1.topdeck_id,
    p2.name AS opponent_name,
    p2.topdeck_id AS opponent_topdeck_id,
    gp1.result
  FROM game_participants gp1
  JOIN game_participants gp2 ON gp2.game_id = gp1.game_id
    AND gp2.entry_id != gp1.entry_id
  JOIN tournament_entries te1 ON te1.id = gp1.entry_id
  JOIN tournament_entries te2 ON te2.id = gp2.entry_id
  JOIN players p1 ON p1.id = te1.player_id
  JOIN players p2 ON p2.id = te2.player_id
)
SELECT
  player_name,
  topdeck_id,
  opponent_name,
  opponent_topdeck_id,
  COUNT(*) as games,
  COUNT(*) FILTER (WHERE result = 'win') as wins,
  COUNT(*) FILTER (WHERE result = 'loss') as losses,
  COUNT(*) FILTER (WHERE result = 'draw') as draws,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE result = 'win') / COUNT(*),
    1
  ) as win_pct
FROM game_results
GROUP BY player_name, topdeck_id, opponent_name, opponent_topdeck_id
HAVING COUNT(*) >= 5  -- Only matchups with 5+ games
ORDER BY games DESC
LIMIT 100;
