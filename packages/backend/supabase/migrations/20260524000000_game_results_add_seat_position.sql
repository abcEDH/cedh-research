-- Add seat_position to regional_elo_game_results so the Elo pipeline
-- can use per-game seat data for tiebreaking without filtering on
-- non-embedded resources (which triggers PGRST108 in PostgREST 11+).
--
-- NOTE: CREATE OR REPLACE VIEW only allows appending new columns, not
-- inserting them mid-list. seat_position is added at the end.

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
  g.table_number,
  gp.seat_position
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
JOIN tournaments t ON g.tournament_id = t.id;

-- Refresh alias so SELECT * picks up seat_position.
CREATE OR REPLACE VIEW global_elo_game_results AS
SELECT * FROM regional_elo_game_results;

-- Restore security_invoker on both views (CREATE OR REPLACE resets view options).
-- Both were marked security_invoker in prior migrations:
--   regional_elo_game_results: 20260408010000_include_unknown_state_global_elo_games.sql
--   global_elo_game_results:   20260408020000_global_elo_table_names.sql
ALTER VIEW regional_elo_game_results SET (security_invoker = true);
ALTER VIEW global_elo_game_results SET (security_invoker = true);
