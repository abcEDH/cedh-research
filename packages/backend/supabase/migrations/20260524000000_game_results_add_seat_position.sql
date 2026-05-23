-- Add seat_position to regional_elo_game_results so the Elo pipeline
-- can use per-game seat data for tiebreaking without filtering on
-- non-embedded resources (which triggers PGRST108 in PostgREST 11+).

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
  gp.seat_position,
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

-- Refresh the alias so SELECT * picks up the new column.
CREATE OR REPLACE VIEW global_elo_game_results AS
SELECT * FROM regional_elo_game_results;
