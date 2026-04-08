-- Persist active leaderboard slices and compact player profile summaries for faster page loads.

CREATE TABLE IF NOT EXISTS global_elo_active_leaderboard (
  region_type text NOT NULL,
  region_key text NOT NULL,
  country_key text,
  player_id uuid NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  player_name text NOT NULL,
  topdeck_id text,
  rank integer NOT NULL,
  rating numeric NOT NULL,
  games_played integer NOT NULL,
  wins integer NOT NULL,
  draws integer NOT NULL,
  losses integer NOT NULL,
  last_game_date date,
  primary_country_key text,
  primary_region_key text,
  activity_score numeric,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (region_type, region_key, player_id)
);

CREATE INDEX IF NOT EXISTS global_elo_active_leaderboard_region_rank_idx
  ON global_elo_active_leaderboard (region_type, region_key, rank);

CREATE INDEX IF NOT EXISTS global_elo_active_leaderboard_player_idx
  ON global_elo_active_leaderboard (player_id, region_type, region_key);

CREATE TABLE IF NOT EXISTS global_elo_player_profile_summaries (
  player_id uuid PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
  topdeck_id text UNIQUE,
  player_name text NOT NULL,
  games_played integer NOT NULL,
  wins integer NOT NULL,
  draws integer NOT NULL,
  losses integer NOT NULL,
  last_game_date date,
  home_country_key text,
  home_region_key text,
  state_assignments jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS global_elo_player_profile_summaries_topdeck_idx
  ON global_elo_player_profile_summaries (topdeck_id);

CREATE INDEX IF NOT EXISTS global_elo_player_profile_summaries_home_region_idx
  ON global_elo_player_profile_summaries (home_country_key, home_region_key);

ALTER TABLE global_elo_active_leaderboard ENABLE ROW LEVEL SECURITY;
ALTER TABLE global_elo_player_profile_summaries ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON global_elo_active_leaderboard;
CREATE POLICY "Public read access"
ON global_elo_active_leaderboard
FOR SELECT
USING (true);

DROP POLICY IF EXISTS "Public read access" ON global_elo_player_profile_summaries;
CREATE POLICY "Public read access"
ON global_elo_player_profile_summaries
FOR SELECT
USING (true);

CREATE OR REPLACE VIEW regional_elo_active_leaderboard AS
SELECT * FROM global_elo_active_leaderboard;

CREATE OR REPLACE VIEW regional_elo_player_profile_summaries AS
SELECT * FROM global_elo_player_profile_summaries;

ALTER VIEW regional_elo_active_leaderboard SET (security_invoker = true);
ALTER VIEW regional_elo_player_profile_summaries SET (security_invoker = true);

GRANT SELECT ON global_elo_active_leaderboard TO anon, authenticated;
GRANT SELECT ON global_elo_player_profile_summaries TO anon, authenticated;
GRANT SELECT ON regional_elo_active_leaderboard TO anon, authenticated;
GRANT SELECT ON regional_elo_player_profile_summaries TO anon, authenticated;
