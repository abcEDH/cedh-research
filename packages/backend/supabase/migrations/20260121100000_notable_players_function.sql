-- Migration: Notable Players by Commander Function
-- Required by: Frontend /commanders/[id] Players tab

-- Function: Get notable players for a specific commander
-- Returns players with 2+ tournament entries using this commander
CREATE OR REPLACE FUNCTION get_notable_players_for_commander(p_commander_id UUID)
RETURNS TABLE (
    player_name TEXT,
    entries BIGINT,
    total_wins BIGINT,
    total_games BIGINT,
    win_rate NUMERIC,
    top_16_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.name as player_name,
        COUNT(te.id) as entries,
        SUM(te.wins)::BIGINT as total_wins,
        SUM(te.wins + te.losses + te.draws)::BIGINT as total_games,
        ROUND(SUM(te.wins)::numeric / NULLIF(SUM(te.wins + te.losses + te.draws), 0), 4) as win_rate,
        SUM(CASE WHEN te.made_top_16 THEN 1 ELSE 0 END)::BIGINT as top_16_count
    FROM tournament_entries te
    JOIN players p ON te.player_id = p.id
    WHERE te.commander_id = p_commander_id
    GROUP BY p.id, p.name
    HAVING COUNT(te.id) >= 2
    ORDER BY COUNT(te.id) DESC, SUM(te.wins) DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID) TO anon;
GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_notable_players_for_commander(UUID) TO service_role;
