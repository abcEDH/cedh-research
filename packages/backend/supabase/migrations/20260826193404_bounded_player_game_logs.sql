-- Bound the player-profile payload and collapse its many PostgREST reads into
-- one database call. The function is intentionally SECURITY INVOKER so the
-- caller retains the same RLS privileges as direct table reads.
DROP FUNCTION IF EXISTS public.get_player_game_logs(uuid, integer);

CREATE OR REPLACE FUNCTION public.get_player_game_logs(
  p_player_id uuid,
  p_limit integer DEFAULT 500,
  p_offset integer DEFAULT 0
)
RETURNS TABLE (
  game_id uuid,
  game_date timestamptz,
  tournament_name text,
  state text,
  round_number integer,
  round_name text,
  table_number integer,
  seat_position integer,
  commander_name text,
  game_result text,
  tournament_player_count integer,
  ranking_eligible boolean,
  opponents jsonb
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $$
  WITH player_games AS (
    SELECT
      g.id AS game_id,
      t.start_date AS game_date,
      t.name AS tournament_name,
      t.state,
      g.round_number,
      g.round_name,
      g.table_number,
      gp.seat_position,
      c.name AS commander_name,
      gp.result AS game_result,
      t.player_count AS tournament_player_count,
      (
        t.player_count >= 30
        AND t.start_date::date <= CURRENT_DATE
        AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
        AND COALESCE(t.topdeck_tid, '') NOT ILIKE '%league%'
        AND t.name NOT ILIKE '%league%'
        AND t.name NOT ILIKE '%casual%'
        AND t.name NOT ILIKE '%exhibition%'
        AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)'
      ) AS ranking_eligible
    FROM public.tournament_entries te
    JOIN public.game_participants gp ON gp.entry_id = te.id
    JOIN public.games g ON g.id = gp.game_id
    JOIN public.tournaments t ON t.id = g.tournament_id
    LEFT JOIN public.commanders c ON c.id = te.commander_id
    WHERE te.player_id = p_player_id
    ORDER BY t.start_date DESC NULLS LAST, g.id
    LIMIT LEAST(GREATEST(COALESCE(p_limit, 500), 1), 500)
    OFFSET GREATEST(COALESCE(p_offset, 0), 0)
  )
  SELECT
    pg.game_id,
    pg.game_date,
    pg.tournament_name,
    pg.state,
    pg.round_number,
    pg.round_name,
    pg.table_number,
    pg.seat_position,
    pg.commander_name,
    pg.game_result,
    pg.tournament_player_count,
    pg.ranking_eligible,
    COALESCE(opponents.rows, '[]'::jsonb) AS opponents
  FROM player_games pg
  LEFT JOIN LATERAL (
    SELECT jsonb_agg(
      jsonb_build_object(
        'topdeckId', opponent.topdeck_id,
        'playerName', COALESCE(opponent.name, 'Unknown'),
        'commanderName', opponent.commander_name,
        'seat', opponent.seat_position + 1,
        'result', opponent.result
      )
      ORDER BY opponent.seat_position
    ) AS rows
    FROM (
      SELECT
        p.topdeck_id,
        p.name,
        c.name AS commander_name,
        gp.seat_position,
        gp.result
      FROM public.game_participants gp
      JOIN public.tournament_entries te ON te.id = gp.entry_id
      JOIN public.players p ON p.id = te.player_id
      LEFT JOIN public.commanders c ON c.id = te.commander_id
      WHERE gp.game_id = pg.game_id
        AND te.player_id <> p_player_id
    ) opponent
  ) opponents ON true
  ORDER BY pg.game_date DESC NULLS LAST, pg.game_id;
$$;

REVOKE ALL ON FUNCTION public.get_player_game_logs(uuid, integer, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_player_game_logs(uuid, integer, integer) TO anon, authenticated;

COMMENT ON FUNCTION public.get_player_game_logs(uuid, integer, integer) IS
  'Returns one page of at most 500 player games with opponents for bounded, complete pagination.';
