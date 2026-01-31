-- View: Player's journey through a tournament (table, seat, result each round)
CREATE OR REPLACE VIEW player_tournament_journey AS
SELECT
  t.name as tournament,
  t.start_date,
  p.name as player,
  c.name as commander,
  g.round_number,
  g.round_name,
  g.table_number,
  gp.seat_position + 1 as seat,
  gp.result,
  g.is_draw
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
LEFT JOIN commanders c ON te.commander_id = c.id
JOIN tournaments t ON g.tournament_id = t.id;

-- View: Pod composition for each game (who was at each table)
CREATE OR REPLACE VIEW pod_composition AS
SELECT
  t.name as tournament,
  t.start_date,
  g.round_number,
  g.round_name,
  g.table_number,
  g.is_draw,
  gp.seat_position + 1 as seat,
  p.name as player,
  c.name as commander,
  gp.result,
  CASE WHEN gp.result = 'win' THEN true ELSE false END as won
FROM games g
JOIN game_participants gp ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
LEFT JOIN commanders c ON te.commander_id = c.id
JOIN tournaments t ON g.tournament_id = t.id;

-- View: Player seat distribution across all games
CREATE OR REPLACE VIEW player_seat_distribution AS
SELECT
  p.name as player,
  COUNT(*) as total_games,
  SUM(CASE WHEN gp.seat_position = 0 THEN 1 ELSE 0 END) as seat_1_count,
  SUM(CASE WHEN gp.seat_position = 1 THEN 1 ELSE 0 END) as seat_2_count,
  SUM(CASE WHEN gp.seat_position = 2 THEN 1 ELSE 0 END) as seat_3_count,
  SUM(CASE WHEN gp.seat_position = 3 THEN 1 ELSE 0 END) as seat_4_count,
  ROUND(SUM(CASE WHEN gp.result = 'win' THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate
FROM game_participants gp
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN players p ON te.player_id = p.id
GROUP BY p.name
HAVING COUNT(*) >= 3;

-- Grant read access
GRANT SELECT ON player_tournament_journey TO anon, authenticated;
GRANT SELECT ON pod_composition TO anon, authenticated;
GRANT SELECT ON player_seat_distribution TO anon, authenticated;
