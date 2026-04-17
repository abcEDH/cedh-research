-- Store TopDeck's published global EDH Elo snapshot separately from local Elo calculations.

CREATE TABLE IF NOT EXISTS topdeck_player_elos (
  topdeck_id text PRIMARY KEY,
  player_id uuid REFERENCES players(id) ON DELETE SET NULL,
  name text NOT NULL,
  username text,
  profile_image_url text,
  elo numeric NOT NULL,
  games_played integer NOT NULL,
  ranking integer NOT NULL,
  source_url text NOT NULL DEFAULT 'https://images.topdeck.gg/elo/magic-the-gathering-edh.json',
  fetched_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS topdeck_player_elos_player_idx
  ON topdeck_player_elos (player_id);

CREATE INDEX IF NOT EXISTS topdeck_player_elos_ranking_idx
  ON topdeck_player_elos (ranking);

CREATE INDEX IF NOT EXISTS topdeck_player_elos_elo_idx
  ON topdeck_player_elos (elo DESC);

ALTER TABLE topdeck_player_elos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read access" ON topdeck_player_elos;
CREATE POLICY "Public read access"
ON topdeck_player_elos
FOR SELECT
USING (true);

GRANT SELECT ON topdeck_player_elos TO anon, authenticated;
