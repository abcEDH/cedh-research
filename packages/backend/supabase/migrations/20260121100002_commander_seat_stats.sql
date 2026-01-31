-- Migration: Commander Seat Stats Materialized View
-- Required by: Frontend /turn-order commander grouping

-- Drop if exists for idempotency
DROP MATERIALIZED VIEW IF EXISTS commander_seat_stats;

-- Materialized view: Commander performance by seat position
CREATE MATERIALIZED VIEW commander_seat_stats AS
SELECT
    c.id as commander_id,
    c.name as commander_name,
    gp.seat_position,
    COUNT(*) as games,
    SUM(CASE WHEN gp.result = 'win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN gp.result = 'loss' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN gp.result = 'draw' THEN 1 ELSE 0 END) as draws,
    ROUND(SUM(CASE WHEN gp.result = 'win' THEN 1 ELSE 0 END)::numeric / COUNT(*), 4) as win_rate,
    ROUND(SUM(CASE WHEN gp.result IN ('win', 'draw') THEN 1 ELSE 0 END)::numeric / COUNT(*), 4) as win_plus_draw_rate
FROM game_participants gp
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN commanders c ON te.commander_id = c.id
WHERE gp.result != 'bye'
GROUP BY c.id, c.name, gp.seat_position
HAVING COUNT(*) >= 10;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX idx_commander_seat_stats_pk
ON commander_seat_stats(commander_id, seat_position);

-- Index for fast lookups
CREATE INDEX idx_commander_seat_stats_commander
ON commander_seat_stats(commander_id);

CREATE INDEX idx_commander_seat_stats_position
ON commander_seat_stats(seat_position);

-- Grant access
GRANT SELECT ON commander_seat_stats TO anon;
GRANT SELECT ON commander_seat_stats TO authenticated;
GRANT SELECT ON commander_seat_stats TO service_role;
