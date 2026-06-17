-- Materialize regional_elo_data_validity
--
-- The plain VIEW aggregated the full game history on every request (~45s over
-- ~290k games / ~1.09M participants), which exceeds the PostgREST statement
-- timeout and broke the maintenance benchmark after each Elo recompute.
--
-- Convert it to a MATERIALIZED VIEW refreshed alongside the other downstream
-- views during the recompute. The query body is unchanged; only the storage and
-- refresh strategy change.

DROP VIEW IF EXISTS regional_elo_data_validity;
DROP MATERIALIZED VIEW IF EXISTS regional_elo_data_validity;

CREATE MATERIALIZED VIEW regional_elo_data_validity AS
WITH game_rows AS (
  SELECT
    g.id AS game_id,
    g.tournament_id,
    t.start_date::date AS game_date,
    UPPER(NULLIF(BTRIM(t.state), '')) AS region_key,
    COUNT(*) FILTER (WHERE gp.result <> 'bye') AS active_participants,
    BOOL_OR(gp.result = 'bye') AS has_bye
  FROM games g
  JOIN tournaments t ON t.id = g.tournament_id
  JOIN game_participants gp ON gp.game_id = g.id
  GROUP BY g.id, g.tournament_id, t.start_date::date, UPPER(NULLIF(BTRIM(t.state), ''))
),
included_games AS (
  SELECT *
  FROM game_rows
  WHERE region_key IS NOT NULL
    AND active_participants >= 2
    AND NOT has_bye
),
included_players AS (
  SELECT DISTINCT
    ig.region_key,
    te.player_id
  FROM included_games ig
  JOIN game_participants gp ON gp.game_id = ig.game_id
  JOIN tournament_entries te ON te.id = gp.entry_id
  WHERE gp.result <> 'bye'
),
region_rows AS (
  SELECT
    'state'::text AS region_type,
    gr.region_key,
    'region'::text AS scope,
    COUNT(DISTINCT gr.tournament_id)::bigint AS total_tournaments,
    COUNT(DISTINCT gr.tournament_id)::bigint AS tournaments_with_state,
    0::bigint AS tournaments_missing_state,
    COUNT(*)::bigint AS total_games,
    COUNT(*) FILTER (
      WHERE gr.active_participants >= 2
        AND NOT gr.has_bye
    )::bigint AS included_games,
    0::bigint AS excluded_games_missing_state,
    COUNT(*) FILTER (WHERE gr.has_bye)::bigint AS excluded_games_with_byes,
    COUNT(*) FILTER (
      WHERE gr.active_participants < 2
        AND NOT gr.has_bye
    )::bigint AS excluded_games_insufficient_players,
    COALESCE(
      (
        SELECT COUNT(DISTINCT ip.player_id)::bigint
        FROM included_players ip
        WHERE ip.region_key = gr.region_key
      ),
      0
    ) AS included_players,
    MIN(gr.game_date) FILTER (
      WHERE gr.active_participants >= 2
        AND NOT gr.has_bye
    ) AS earliest_game_date,
    MAX(gr.game_date) FILTER (
      WHERE gr.active_participants >= 2
        AND NOT gr.has_bye
    ) AS latest_game_date
  FROM game_rows gr
  WHERE gr.region_key IS NOT NULL
  GROUP BY gr.region_key
),
global_row AS (
  SELECT
    'state'::text AS region_type,
    NULL::text AS region_key,
    'global'::text AS scope,
    COUNT(DISTINCT gr.tournament_id)::bigint AS total_tournaments,
    COUNT(DISTINCT gr.tournament_id) FILTER (WHERE gr.region_key IS NOT NULL)::bigint AS tournaments_with_state,
    COUNT(DISTINCT gr.tournament_id) FILTER (WHERE gr.region_key IS NULL)::bigint AS tournaments_missing_state,
    COUNT(*)::bigint AS total_games,
    COUNT(*) FILTER (
      WHERE gr.region_key IS NOT NULL
        AND gr.active_participants >= 2
        AND NOT gr.has_bye
    )::bigint AS included_games,
    COUNT(*) FILTER (WHERE gr.region_key IS NULL)::bigint AS excluded_games_missing_state,
    COUNT(*) FILTER (WHERE gr.region_key IS NOT NULL AND gr.has_bye)::bigint AS excluded_games_with_byes,
    COUNT(*) FILTER (
      WHERE gr.region_key IS NOT NULL
        AND gr.active_participants < 2
        AND NOT gr.has_bye
    )::bigint AS excluded_games_insufficient_players,
    (
      SELECT COUNT(DISTINCT te.player_id)::bigint
      FROM included_games ig
      JOIN game_participants gp ON gp.game_id = ig.game_id
      JOIN tournament_entries te ON te.id = gp.entry_id
      WHERE gp.result <> 'bye'
    ) AS included_players,
    MIN(gr.game_date) FILTER (
      WHERE gr.region_key IS NOT NULL
        AND gr.active_participants >= 2
        AND NOT gr.has_bye
    ) AS earliest_game_date,
    MAX(gr.game_date) FILTER (
      WHERE gr.region_key IS NOT NULL
        AND gr.active_participants >= 2
        AND NOT gr.has_bye
    ) AS latest_game_date
  FROM game_rows gr
)
SELECT * FROM global_row
UNION ALL
SELECT * FROM region_rows;

-- Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY.
-- (scope, region_key) uniquely identifies every row: the single global row
-- (scope='global', region_key NULL) and one row per state (scope='region').
CREATE UNIQUE INDEX idx_regional_elo_data_validity_pk
  ON regional_elo_data_validity (scope, region_key);
CREATE INDEX idx_regional_elo_data_validity_region_key
  ON regional_elo_data_validity (region_key);

GRANT SELECT ON regional_elo_data_validity TO anon, authenticated, service_role;

COMMENT ON MATERIALIZED VIEW regional_elo_data_validity IS
  'State leaderboard coverage stats (global + per-region). Materialized; refreshed during the Elo recompute via refresh_regional_elo_data_validity().';

-- ============================================================================
-- FUNCTION: Refresh regional_elo_data_validity
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_regional_elo_data_validity()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY regional_elo_data_validity;
END;
$$ LANGUAGE plpgsql;

GRANT EXECUTE ON FUNCTION refresh_regional_elo_data_validity() TO service_role;

COMMENT ON FUNCTION refresh_regional_elo_data_validity IS
  'Refreshes the regional_elo_data_validity materialized view (CONCURRENTLY).';
