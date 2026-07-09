-- Scope the Elo pipeline's game feed to cEDH (ADR 0015 multi-game expansion).
--
-- Non-cEDH tournaments (Riftbound, Gundam TCG, Yu-Gi-Oh) are about to be
-- ingested into the same tables. The regional/global Elo models are cEDH-only,
-- so regional_elo_game_results gains an explicit game/format guard.
--
-- NOTE: CREATE OR REPLACE VIEW only allows appending new columns, not
-- inserting or reordering them (see 20260524000000). The column list below is
-- byte-for-byte the 20260524000000 definition; only the WHERE clause is new.

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
JOIN tournaments t ON g.tournament_id = t.id
WHERE t.game = 'Magic: The Gathering' AND t.format = 'EDH';

-- global_elo_game_results (20260408020000 / 20260524000000) is defined as
-- SELECT * FROM regional_elo_game_results. The column list is unchanged, so it
-- does not need recreation and automatically inherits the cEDH guard.

-- Restore security_invoker (CREATE OR REPLACE resets view options). Re-assert
-- it on the global alias as well, matching the 20260524000000 convention.
ALTER VIEW regional_elo_game_results SET (security_invoker = true);
ALTER VIEW global_elo_game_results SET (security_invoker = true);

-- Re-apply the grants from 20260408010000 / 20260408020000.
GRANT SELECT ON regional_elo_game_results TO anon, authenticated;
GRANT SELECT ON global_elo_game_results TO anon, authenticated;
