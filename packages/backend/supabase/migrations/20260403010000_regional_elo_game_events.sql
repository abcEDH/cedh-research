-- Persist per-game regional Elo events so player drilldowns can justify rating changes.

CREATE TABLE IF NOT EXISTS regional_elo_game_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  region_type text NOT NULL,
  region_key text NOT NULL,
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  tournament_id uuid NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
  player_id uuid NOT NULL REFERENCES players(id) ON DELETE CASCADE,
  entry_id uuid NOT NULL REFERENCES tournament_entries(id) ON DELETE CASCADE,
  game_date timestamptz,
  game_result text NOT NULL,
  is_draw boolean NOT NULL DEFAULT false,
  opponent_count integer NOT NULL DEFAULT 0,
  expected_score numeric NOT NULL,
  actual_score numeric NOT NULL,
  rating_before numeric NOT NULL,
  rating_delta numeric NOT NULL,
  rating_after numeric NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (region_type, region_key, game_id, player_id)
);

CREATE INDEX IF NOT EXISTS regional_elo_game_events_region_idx
  ON regional_elo_game_events (region_type, region_key, game_date DESC);

CREATE INDEX IF NOT EXISTS regional_elo_game_events_player_idx
  ON regional_elo_game_events (player_id, game_date DESC);

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
JOIN game_participants gp ON gp.game_id = e.game_id AND gp.entry_id = e.entry_id;

GRANT SELECT ON regional_elo_game_events TO anon, authenticated;
GRANT SELECT ON regional_elo_game_event_log TO anon, authenticated;
