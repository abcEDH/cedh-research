-- Persist compact per-player commander profiles for fast leaderboard and drilldown reads.

CREATE TABLE IF NOT EXISTS player_commander_profiles (
  player_id uuid PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
  topdeck_id text NOT NULL UNIQUE,
  player_name text,
  active_commander text,
  active_commander_entries integer NOT NULL DEFAULT 0,
  active_commander_prediction_score numeric NOT NULL DEFAULT 0,
  total_entries integer NOT NULL DEFAULT 0,
  commander_predictions jsonb NOT NULL DEFAULT '[]'::jsonb,
  latest_commander text,
  latest_commander_date date,
  latest_decklist_url text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS player_commander_profiles_active_commander_idx
  ON player_commander_profiles (active_commander);

CREATE INDEX IF NOT EXISTS player_commander_profiles_updated_at_idx
  ON player_commander_profiles (updated_at DESC);

ALTER TABLE player_commander_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON player_commander_profiles;
CREATE POLICY "Public read access"
ON player_commander_profiles
FOR SELECT
USING (true);

GRANT SELECT ON player_commander_profiles TO anon, authenticated;
