-- Survival Analysis Views for cEDH Analytics
-- Three categories: Pod survival, Tournament survival, Meta survival

-- Drop existing views to avoid column mismatch errors
DROP VIEW IF EXISTS seat_survival_by_commander CASCADE;
DROP VIEW IF EXISTS seat_survival_by_round CASCADE;
DROP VIEW IF EXISTS commander_survival_curve CASCADE;
DROP VIEW IF EXISTS commander_tournament_depth CASCADE;
DROP VIEW IF EXISTS player_survival_stats CASCADE;
DROP VIEW IF EXISTS commander_meta_monthly CASCADE;
DROP VIEW IF EXISTS commander_momentum CASCADE;
DROP VIEW IF EXISTS commander_first_appearances CASCADE;
DROP VIEW IF EXISTS survival_summary CASCADE;

-- ============================================================================
-- POD SURVIVAL: Turn order / seat position analysis
-- ============================================================================

-- Enhanced seat position stats by commander
CREATE OR REPLACE VIEW seat_survival_by_commander AS
SELECT
    c.name AS commander_name,
    gp.seat_position,
    COUNT(*) AS games_played,
    COUNT(*) FILTER (WHERE gp.result = 'win') AS wins,
    COUNT(*) FILTER (WHERE gp.result = 'loss') AS losses,
    COUNT(*) FILTER (WHERE gp.result = 'draw') AS draws,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
        4
    ) AS win_rate,
    -- Compare to baseline (25% expected)
    ROUND(
        (COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0)) - 0.25,
        4
    ) AS win_rate_vs_expected
FROM game_participants gp
JOIN games g ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN commanders c ON te.commander_id = c.id
WHERE g.status = 'Completed' AND gp.result != 'bye'
GROUP BY c.name, gp.seat_position
HAVING COUNT(*) >= 10  -- Minimum sample size
ORDER BY c.name, gp.seat_position;

-- Seat position performance by round (early vs late game advantage)
CREATE OR REPLACE VIEW seat_survival_by_round AS
SELECT
    g.round_number,
    gp.seat_position,
    COUNT(*) AS games_played,
    COUNT(*) FILTER (WHERE gp.result = 'win') AS wins,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
        4
    ) AS win_rate
FROM game_participants gp
JOIN games g ON gp.game_id = g.id
WHERE g.status = 'Completed'
  AND gp.result != 'bye'
  AND NOT g.is_bracket
  AND g.round_number IS NOT NULL
GROUP BY g.round_number, gp.seat_position
ORDER BY g.round_number, gp.seat_position;

-- ============================================================================
-- TOURNAMENT SURVIVAL: Elimination & progression analysis
-- ============================================================================

-- Commander survival curve: win rate by round number
CREATE OR REPLACE VIEW commander_survival_curve AS
SELECT
    c.name AS commander_name,
    g.round_number,
    COUNT(*) AS games_played,
    COUNT(*) FILTER (WHERE gp.result = 'win') AS wins,
    COUNT(*) FILTER (WHERE gp.result = 'loss') AS losses,
    ROUND(
        COUNT(*) FILTER (WHERE gp.result = 'win')::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE gp.result != 'bye'), 0),
        4
    ) AS win_rate,
    -- Cumulative win count for survival analysis
    SUM(COUNT(*) FILTER (WHERE gp.result = 'win')) OVER (
        PARTITION BY c.name ORDER BY g.round_number
    ) AS cumulative_wins,
    SUM(COUNT(*) FILTER (WHERE gp.result = 'loss')) OVER (
        PARTITION BY c.name ORDER BY g.round_number
    ) AS cumulative_losses
FROM game_participants gp
JOIN games g ON gp.game_id = g.id
JOIN tournament_entries te ON gp.entry_id = te.id
JOIN commanders c ON te.commander_id = c.id
WHERE g.status = 'Completed'
  AND NOT g.is_bracket
  AND g.round_number IS NOT NULL
GROUP BY c.name, g.round_number
HAVING COUNT(*) >= 5
ORDER BY c.name, g.round_number;

-- Tournament depth: how deep commanders go on average
CREATE OR REPLACE VIEW commander_tournament_depth AS
SELECT
    c.name AS commander_name,
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments,
    ROUND(AVG(te.wins + te.draws * 0.5), 2) AS avg_match_points,
    ROUND(AVG(te.wins), 2) AS avg_wins,
    ROUND(AVG(te.losses), 2) AS avg_losses,
    ROUND(AVG(te.final_standing), 1) AS avg_standing,
    -- Percentile ranking within tournaments
    ROUND(AVG(
        te.final_standing::NUMERIC / NULLIF(t.player_count, 0)
    ), 4) AS avg_percentile,
    COUNT(*) FILTER (WHERE te.made_top_cut) AS top_cuts,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16s,
    COUNT(*) FILTER (WHERE te.final_standing = 1) AS tournament_wins,
    ROUND(
        COUNT(*) FILTER (WHERE te.made_top_cut)::NUMERIC /
        NULLIF(COUNT(*), 0),
        4
    ) AS top_cut_rate,
    ROUND(
        COUNT(*) FILTER (WHERE te.final_standing = 1)::NUMERIC /
        NULLIF(COUNT(*), 0),
        4
    ) AS win_rate
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
GROUP BY c.name
HAVING COUNT(DISTINCT te.id) >= 5
ORDER BY avg_percentile ASC;  -- Lower percentile = better (closer to 1st place)

-- Player survival: how consistent are top players
CREATE OR REPLACE VIEW player_survival_stats AS
SELECT
    p.name AS player_name,
    COUNT(DISTINCT te.id) AS tournaments_played,
    ROUND(AVG(te.wins), 2) AS avg_wins,
    ROUND(AVG(te.losses), 2) AS avg_losses,
    ROUND(AVG(te.final_standing), 1) AS avg_standing,
    COUNT(*) FILTER (WHERE te.made_top_cut) AS top_cuts,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16s,
    COUNT(*) FILTER (WHERE te.final_standing = 1) AS wins,
    ROUND(
        COUNT(*) FILTER (WHERE te.made_top_cut)::NUMERIC /
        NULLIF(COUNT(*), 0),
        4
    ) AS top_cut_rate,
    -- Consistency score: inverse of standard deviation of standings
    ROUND(STDDEV(te.final_standing), 2) AS standing_stddev,
    -- Most played commander
    MODE() WITHIN GROUP (ORDER BY c.name) AS main_commander
FROM players p
JOIN tournament_entries te ON p.id = te.player_id
JOIN tournaments t ON te.tournament_id = t.id
JOIN commanders c ON te.commander_id = c.id
WHERE t.player_count >= 32
GROUP BY p.id, p.name
HAVING COUNT(DISTINCT te.id) >= 3
ORDER BY top_cut_rate DESC, tournaments_played DESC;

-- ============================================================================
-- META SURVIVAL: Temporal trends and momentum
-- ============================================================================

-- Commander meta share over time (monthly)
CREATE OR REPLACE VIEW commander_meta_monthly AS
SELECT
    DATE_TRUNC('month', t.start_date) AS month,
    c.name AS commander_name,
    COUNT(DISTINCT te.id) AS entries,
    -- Meta share for this month
    ROUND(
        COUNT(DISTINCT te.id)::NUMERIC /
        SUM(COUNT(DISTINCT te.id)) OVER (PARTITION BY DATE_TRUNC('month', t.start_date)),
        4
    ) AS meta_share,
    -- Performance metrics
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16_count,
    ROUND(
        COUNT(*) FILTER (WHERE te.made_top_16)::NUMERIC / NULLIF(COUNT(*), 0),
        4
    ) AS top_16_rate
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
GROUP BY DATE_TRUNC('month', t.start_date), c.name
HAVING COUNT(DISTINCT te.id) >= 3
ORDER BY month DESC, entries DESC;

-- Commander momentum: rising and falling commanders
CREATE OR REPLACE VIEW commander_momentum AS
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', t.start_date) AS month,
        c.name AS commander_name,
        COUNT(DISTINCT te.id) AS entries,
        ROUND(
            COUNT(DISTINCT te.id)::NUMERIC /
            SUM(COUNT(DISTINCT te.id)) OVER (PARTITION BY DATE_TRUNC('month', t.start_date)),
            4
        ) AS meta_share,
        ROUND(AVG(te.win_rate), 4) AS avg_win_rate
    FROM commanders c
    JOIN tournament_entries te ON c.id = te.commander_id
    JOIN tournaments t ON te.tournament_id = t.id
    WHERE t.player_count >= 32
    GROUP BY DATE_TRUNC('month', t.start_date), c.name
    HAVING COUNT(DISTINCT te.id) >= 2
),
with_lag AS (
    SELECT
        *,
        LAG(meta_share) OVER (PARTITION BY commander_name ORDER BY month) AS prev_meta_share,
        LAG(avg_win_rate) OVER (PARTITION BY commander_name ORDER BY month) AS prev_win_rate
    FROM monthly_stats
)
SELECT
    month,
    commander_name,
    entries,
    meta_share,
    prev_meta_share,
    ROUND(meta_share - COALESCE(prev_meta_share, 0), 4) AS meta_share_delta,
    avg_win_rate,
    prev_win_rate,
    ROUND(avg_win_rate - COALESCE(prev_win_rate, 0), 4) AS win_rate_delta,
    -- Momentum score: combination of meta share growth and win rate growth
    ROUND(
        (COALESCE(meta_share - prev_meta_share, 0) * 100) +
        (COALESCE(avg_win_rate - prev_win_rate, 0) * 100),
        2
    ) AS momentum_score
FROM with_lag
WHERE month = (SELECT MAX(month) FROM with_lag)  -- Latest month only
ORDER BY momentum_score DESC;

-- New commanders emerging in the meta
CREATE OR REPLACE VIEW commander_first_appearances AS
SELECT
    c.name AS commander_name,
    MIN(t.start_date) AS first_seen,
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments,
    ROUND(AVG(te.win_rate), 4) AS avg_win_rate,
    COUNT(*) FILTER (WHERE te.made_top_16) AS top_16s
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
GROUP BY c.name
ORDER BY first_seen DESC;

-- ============================================================================
-- SUMMARY VIEW: Combined survival metrics
-- ============================================================================

CREATE OR REPLACE VIEW survival_summary AS
SELECT
    c.name AS commander_name,
    -- Volume
    COUNT(DISTINCT te.id) AS total_entries,
    COUNT(DISTINCT t.id) AS tournaments,
    SUM(
        (SELECT COUNT(*) FROM game_participants gp2
         JOIN games g2 ON gp2.game_id = g2.id
         WHERE gp2.entry_id = te.id AND g2.status = 'Completed')
    ) AS total_games,
    -- Pod Survival
    ROUND(AVG(te.win_rate), 4) AS overall_win_rate,
    -- Tournament Survival
    ROUND(AVG(te.final_standing::NUMERIC / NULLIF(t.player_count, 0)), 4) AS avg_percentile,
    COUNT(*) FILTER (WHERE te.made_top_cut)::NUMERIC / NULLIF(COUNT(*), 0) AS top_cut_rate,
    COUNT(*) FILTER (WHERE te.final_standing = 1)::NUMERIC / NULLIF(COUNT(*), 0) AS tournament_win_rate,
    -- Recent performance (last 90 days)
    COUNT(*) FILTER (WHERE t.start_date >= NOW() - INTERVAL '90 days') AS recent_entries,
    ROUND(
        AVG(te.win_rate) FILTER (WHERE t.start_date >= NOW() - INTERVAL '90 days'),
        4
    ) AS recent_win_rate
FROM commanders c
JOIN tournament_entries te ON c.id = te.commander_id
JOIN tournaments t ON te.tournament_id = t.id
WHERE t.player_count >= 32
GROUP BY c.name
HAVING COUNT(DISTINCT te.id) >= 5
ORDER BY total_entries DESC;
