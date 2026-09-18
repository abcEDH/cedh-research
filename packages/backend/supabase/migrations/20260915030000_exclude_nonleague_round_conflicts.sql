-- A source can be internally contradictory. Preserve its rows, but never
-- choose arbitrarily which of two simultaneous non-league games was played.
CREATE OR REPLACE VIEW public.elo_conflicted_games AS
WITH collisions AS (
  SELECT array_agg(DISTINCT g.id) AS game_ids
  FROM public.games g
  JOIN public.tournaments t ON t.id = g.tournament_id
  JOIN public.game_participants gp ON gp.game_id = g.id
  JOIN public.tournament_entries te ON te.id = gp.entry_id
  WHERE NOT COALESCE(t.is_league, false)
    AND t.start_date <= CURRENT_TIMESTAMP
    AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
  GROUP BY g.tournament_id, g.round_number,
    CASE WHEN g.round_number IS NULL THEN g.round_name END,
    g.is_bracket, te.player_id
  HAVING count(DISTINCT g.id) > 1
)
SELECT DISTINCT unnest(game_ids) AS game_id FROM collisions;
ALTER VIEW public.elo_conflicted_games SET (security_invoker = true);
GRANT SELECT ON public.elo_conflicted_games TO anon, authenticated, service_role;

CREATE OR REPLACE VIEW public.regional_elo_game_results AS
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
  gp.seat_position,
  (
    t.player_count >= 30
    AND t.start_date <= CURRENT_TIMESTAMP
    AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
    AND COALESCE(t.topdeck_tid, '') NOT ILIKE '%league%'
    AND t.name NOT ILIKE '%league%'
    AND t.name NOT ILIKE '%casual%'
    AND t.name NOT ILIKE '%exhibition%'
    AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)'
  ) AS ranking_eligible,
  (
    t.player_count >= 10
    AND t.start_date <= CURRENT_TIMESTAMP
    AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
    AND t.name NOT ILIKE '%casual%'
    AND t.name NOT ILIKE '%exhibition%'
    AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)'
  ) AS local_eligible,
  (t.start_date <= CURRENT_TIMESTAMP
   AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')) AS all_eligible
FROM public.games g
JOIN public.game_participants gp ON gp.game_id = g.id
JOIN public.tournament_entries te ON te.id = gp.entry_id
JOIN public.players p ON p.id = te.player_id
JOIN public.tournaments t ON t.id = g.tournament_id
WHERE t.start_date <= CURRENT_TIMESTAMP
  AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
  AND NOT EXISTS (SELECT 1 FROM public.elo_conflicted_games c WHERE c.game_id = g.id);

