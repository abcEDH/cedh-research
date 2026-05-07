-- Keep the public global event-log alias readable without depending on the
-- service-role-only regional view.

CREATE OR REPLACE VIEW public.global_elo_game_event_log AS
SELECT
  e.region_type,
  e.region_key,
  e.game_id,
  e.tournament_id,
  e.player_id,
  p.name AS player_name,
  p.topdeck_id,
  e.entry_id,
  e.game_date,
  t.name AS tournament_name,
  t.state,
  g.round_number,
  g.round_name,
  g.table_number,
  gp.seat_position,
  c.name AS commander_name,
  e.game_result,
  e.is_draw,
  e.opponent_count,
  e.expected_score,
  e.actual_score,
  e.rating_before,
  e.rating_delta,
  e.rating_after
FROM public.global_elo_game_events e
JOIN public.players p ON p.id = e.player_id
JOIN public.tournament_entries te ON te.id = e.entry_id
LEFT JOIN public.commanders c ON c.id = te.commander_id
JOIN public.tournaments t ON t.id = e.tournament_id
JOIN public.games g ON g.id = e.game_id
JOIN public.game_participants gp ON gp.game_id = e.game_id AND gp.entry_id = e.entry_id;

ALTER VIEW public.global_elo_game_event_log SET (security_invoker = true);
GRANT SELECT ON public.global_elo_game_event_log TO anon, authenticated;
