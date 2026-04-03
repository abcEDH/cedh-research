-- Regional Elo data validity drilldown
--
-- Exposes both global and per-region coverage stats so the frontend can explain
-- why some tournaments or games do not appear in the state leaderboard.

CREATE OR REPLACE VIEW regional_elo_data_validity AS
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

GRANT SELECT ON regional_elo_data_validity TO anon, authenticated;
