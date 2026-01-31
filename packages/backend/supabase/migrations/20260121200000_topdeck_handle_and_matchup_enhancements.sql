-- Migration: TopDeck Handle and Matchup Enhancements
-- 1. Add topdeck_handle column to players table
-- 2. Enhance get_commander_matchups with pagination and statistical significance

-- ============================================================================
-- PART 1: Add topdeck_handle column
-- ============================================================================

ALTER TABLE players ADD COLUMN IF NOT EXISTS topdeck_handle TEXT;

-- Index for efficient handle lookups (once populated)
CREATE INDEX IF NOT EXISTS idx_players_topdeck_handle ON players(topdeck_handle);

-- ============================================================================
-- PART 2: Enhanced matchup function with pagination and statistics
-- ============================================================================

-- Drop old function
DROP FUNCTION IF EXISTS get_commander_matchups(UUID);

-- Enhanced version with pagination, min games filter, and statistical significance
CREATE OR REPLACE FUNCTION get_commander_matchups(
    p_commander_id UUID,
    p_limit INT DEFAULT 50,
    p_offset INT DEFAULT 0,
    p_min_games INT DEFAULT 5
)
RETURNS TABLE (
    opponent_commander_id UUID,
    opponent_commander_name TEXT,
    games_played BIGINT,
    wins BIGINT,
    losses BIGINT,
    draws BIGINT,
    win_rate NUMERIC,
    loss_rate NUMERIC,
    draw_rate NUMERIC,
    -- Statistical significance indicators
    expected_win_rate NUMERIC,
    win_rate_vs_expected NUMERIC,
    is_statistically_significant BOOLEAN,
    confidence_level TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH matchup_data AS (
        SELECT
            opp_c.id AS opp_commander_id,
            opp_c.name AS opp_commander_name,
            COUNT(*) AS total_games,
            COUNT(*) FILTER (WHERE gp.result = 'win') AS total_wins,
            COUNT(*) FILTER (WHERE gp.result = 'loss') AS total_losses,
            COUNT(*) FILTER (WHERE gp.result = 'draw') AS total_draws
        FROM game_participants gp
        JOIN tournament_entries te ON gp.entry_id = te.id
        JOIN games g ON gp.game_id = g.id
        JOIN game_participants opp_gp ON g.id = opp_gp.game_id AND opp_gp.id != gp.id
        JOIN tournament_entries opp_te ON opp_gp.entry_id = opp_te.id
        JOIN commanders opp_c ON opp_te.commander_id = opp_c.id
        WHERE te.commander_id = p_commander_id
          AND gp.result != 'bye'
          AND opp_gp.result != 'bye'
        GROUP BY opp_c.id, opp_c.name
        HAVING COUNT(*) >= p_min_games
    )
    SELECT
        md.opp_commander_id,
        md.opp_commander_name,
        md.total_games,
        md.total_wins,
        md.total_losses,
        md.total_draws,
        ROUND(md.total_wins::NUMERIC / md.total_games, 4) AS win_rate,
        ROUND(md.total_losses::NUMERIC / md.total_games, 4) AS loss_rate,
        ROUND(md.total_draws::NUMERIC / md.total_games, 4) AS draw_rate,
        -- Expected win rate in 4-player pod (25%)
        0.25::NUMERIC AS expected_win_rate,
        -- Difference from expected
        ROUND((md.total_wins::NUMERIC / md.total_games) - 0.25, 4) AS win_rate_vs_expected,
        -- Statistical significance (simplified: >20 games = more reliable)
        -- Using Wilson score interval approximation
        CASE
            WHEN md.total_games >= 30 THEN TRUE
            WHEN md.total_games >= 20 AND ABS((md.total_wins::NUMERIC / md.total_games) - 0.25) > 0.10 THEN TRUE
            WHEN md.total_games >= 10 AND ABS((md.total_wins::NUMERIC / md.total_games) - 0.25) > 0.15 THEN TRUE
            ELSE FALSE
        END AS is_statistically_significant,
        -- Confidence level based on sample size
        CASE
            WHEN md.total_games >= 50 THEN 'high'
            WHEN md.total_games >= 30 THEN 'medium'
            WHEN md.total_games >= 15 THEN 'low'
            ELSE 'very_low'
        END AS confidence_level
    FROM matchup_data md
    ORDER BY md.total_games DESC, md.total_wins DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- Also create a count function for pagination
CREATE OR REPLACE FUNCTION get_commander_matchups_count(
    p_commander_id UUID,
    p_min_games INT DEFAULT 5
)
RETURNS BIGINT AS $$
BEGIN
    RETURN (
        SELECT COUNT(DISTINCT opp_te.commander_id)
        FROM game_participants gp
        JOIN tournament_entries te ON gp.entry_id = te.id
        JOIN games g ON gp.game_id = g.id
        JOIN game_participants opp_gp ON g.id = opp_gp.game_id AND opp_gp.id != gp.id
        JOIN tournament_entries opp_te ON opp_gp.entry_id = opp_te.id
        WHERE te.commander_id = p_commander_id
          AND gp.result != 'bye'
          AND opp_gp.result != 'bye'
        GROUP BY opp_te.commander_id
        HAVING COUNT(*) >= p_min_games
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID, INT, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID, INT, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID, INT, INT, INT) TO service_role;

GRANT EXECUTE ON FUNCTION get_commander_matchups_count(UUID, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_commander_matchups_count(UUID, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_commander_matchups_count(UUID, INT) TO service_role;

-- ============================================================================
-- PART 3: Update notable players function to include topdeck_handle
-- ============================================================================

DROP FUNCTION IF EXISTS get_notable_players_for_commander(UUID);

CREATE OR REPLACE FUNCTION get_notable_players_for_commander(
    p_commander_id UUID,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    player_id UUID,
    player_name TEXT,
    topdeck_handle TEXT,
    topdeck_id TEXT,
    entries BIGINT,
    total_wins BIGINT,
    total_losses BIGINT,
    total_draws BIGINT,
    total_games BIGINT,
    win_rate NUMERIC,
    top_16_count BIGINT,
    avg_standing NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS player_id,
        p.name AS player_name,
        p.topdeck_handle,
        p.topdeck_id,
        COUNT(te.id) AS entries,
        SUM(te.wins)::BIGINT AS total_wins,
        SUM(te.losses)::BIGINT AS total_losses,
        SUM(te.draws)::BIGINT AS total_draws,
        SUM(te.wins + te.losses + te.draws)::BIGINT AS total_games,
        ROUND(SUM(te.wins)::NUMERIC / NULLIF(SUM(te.wins + te.losses + te.draws), 0), 4) AS win_rate,
        SUM(CASE WHEN te.made_top_16 THEN 1 ELSE 0 END)::BIGINT AS top_16_count,
        ROUND(AVG(te.final_standing), 1) AS avg_standing
    FROM tournament_entries te
    JOIN players p ON te.player_id = p.id
    WHERE te.commander_id = p_commander_id
    GROUP BY p.id, p.name, p.topdeck_handle, p.topdeck_id
    HAVING COUNT(te.id) >= 2
    ORDER BY COUNT(te.id) DESC, SUM(te.wins) DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID, INT, INT) TO service_role;
