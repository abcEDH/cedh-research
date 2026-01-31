-- Migration: Commander Matchups Function
-- Required by: Frontend /commanders/[id] Matchups tab

-- Function: Get commander vs commander matchup statistics
-- Shows which commanders beat/lose to a specific commander
CREATE OR REPLACE FUNCTION get_commander_matchups(p_commander_id UUID)
RETURNS TABLE (
    opponent_commander TEXT,
    opponent_commander_id UUID,
    times_lost_to BIGINT,
    times_beat BIGINT,
    total_encounters BIGINT,
    loss_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH my_games AS (
        -- Get all games where this commander participated
        SELECT
            gp.game_id,
            gp.result as my_result
        FROM game_participants gp
        JOIN tournament_entries te ON gp.entry_id = te.id
        WHERE te.commander_id = p_commander_id
    ),
    opponent_results AS (
        -- For each game, get opponent commanders and their results
        SELECT
            c.id as opp_commander_id,
            c.name as opp_commander,
            mg.my_result,
            gp.result as opp_result
        FROM my_games mg
        JOIN game_participants gp ON mg.game_id = gp.game_id
        JOIN tournament_entries te ON gp.entry_id = te.id
        JOIN commanders c ON te.commander_id = c.id
        WHERE te.commander_id != p_commander_id
    )
    SELECT
        opp_commander as opponent_commander,
        opp_commander_id as opponent_commander_id,
        SUM(CASE WHEN my_result = 'loss' AND opp_result = 'win' THEN 1 ELSE 0 END)::BIGINT as times_lost_to,
        SUM(CASE WHEN my_result = 'win' AND opp_result = 'loss' THEN 1 ELSE 0 END)::BIGINT as times_beat,
        COUNT(*)::BIGINT as total_encounters,
        ROUND(
            SUM(CASE WHEN my_result = 'loss' AND opp_result = 'win' THEN 1 ELSE 0 END)::numeric
            / NULLIF(COUNT(*), 0),
            4
        ) as loss_rate
    FROM opponent_results
    GROUP BY opp_commander_id, opp_commander
    HAVING COUNT(*) >= 3  -- Minimum 3 encounters for meaningful data
    ORDER BY
        SUM(CASE WHEN my_result = 'loss' AND opp_result = 'win' THEN 1 ELSE 0 END) DESC,
        COUNT(*) DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql STABLE;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID) TO anon;
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_commander_matchups(UUID) TO service_role;
