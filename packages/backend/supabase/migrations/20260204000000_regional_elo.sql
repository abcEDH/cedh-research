-- Regional Elo ratings storage + helper views

CREATE TABLE IF NOT EXISTS regional_elo_ratings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  region_type text NOT NULL,
  region_key text NOT NULL,
  player_id uuid NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  rating numeric NOT NULL DEFAULT 1500,
  games_played integer NOT NULL DEFAULT 0,
  wins integer NOT NULL DEFAULT 0,
  draws integer NOT NULL DEFAULT 0,
  losses integer NOT NULL DEFAULT 0,
  last_game_date date,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (region_type, region_key, player_id)
);

CREATE INDEX IF NOT EXISTS regional_elo_ratings_region_idx
  ON regional_elo_ratings (region_type, region_key, rating DESC);

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
SELECT
  r.region_type,
  r.region_key,
  r.player_id,
  p.name AS player_name,
  p.topdeck_id,
  r.rating,
  r.games_played,
  r.wins,
  r.draws,
  r.losses,
  r.last_game_date,
  r.updated_at,
  ROW_NUMBER() OVER (
    PARTITION BY r.region_type, r.region_key
    ORDER BY r.rating DESC, r.games_played DESC
  ) AS rank
FROM regional_elo_ratings r
JOIN players p ON p.id = r.player_id;

CREATE OR REPLACE VIEW regional_elo_regions AS
SELECT
  region_type,
  region_key,
  COUNT(*) AS player_count,
  MAX(updated_at) AS updated_at
FROM regional_elo_ratings
GROUP BY region_type, region_key;

GRANT SELECT ON regional_elo_game_results TO anon, authenticated;
GRANT SELECT ON regional_elo_leaderboard TO anon, authenticated;
GRANT SELECT ON regional_elo_regions TO anon, authenticated;
