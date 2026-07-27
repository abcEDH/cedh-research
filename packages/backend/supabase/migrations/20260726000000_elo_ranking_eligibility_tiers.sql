-- Canonical eligibility flags for the three public Elo/data tiers.
-- `tournaments.tier` is intentionally not reused: it already stores the
-- TopDeck event tier (Diamond/Platinum/etc.).

CREATE INDEX IF NOT EXISTS idx_tournaments_topdeck_tid
  ON public.tournaments (topdeck_tid);

CREATE INDEX IF NOT EXISTS idx_tournament_entries_decklist_presence
  ON public.tournament_entries (tournament_id, player_id)
  WHERE NULLIF(BTRIM(decklist_text), '') IS NOT NULL
     OR NULLIF(BTRIM(decklist_url), '') IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_games_tournament_status
  ON public.games (tournament_id, status);

-- Preserve the existing global Elo input columns and append the flags so
-- existing consumers remain compatible with CREATE OR REPLACE VIEW rules.
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
    AND t.start_date::date <= CURRENT_DATE
    AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
    AND COALESCE(NULLIF(BTRIM(te.decklist_text), ''), NULLIF(BTRIM(te.decklist_url), '')) IS NOT NULL
    AND COALESCE(t.topdeck_tid, '') NOT ILIKE '%league%'
    AND t.name NOT ILIKE '%league%'
    AND t.name NOT ILIKE '%casual%'
    AND t.name NOT ILIKE '%exhibition%'
    AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)'
  ) AS ranking_eligible,
  (
    t.player_count >= 10
    AND t.start_date::date <= CURRENT_DATE
    AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
    AND t.name NOT ILIKE '%casual%'
    AND t.name NOT ILIKE '%exhibition%'
    AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)'
  ) AS local_eligible,
  (t.start_date IS NOT NULL) AS all_eligible
FROM public.games g
JOIN public.game_participants gp ON gp.game_id = g.id
JOIN public.tournament_entries te ON te.id = gp.entry_id
JOIN public.players p ON p.id = te.player_id
JOIN public.tournaments t ON t.id = g.tournament_id;

CREATE OR REPLACE VIEW public.global_elo_game_results AS
SELECT * FROM public.regional_elo_game_results;

ALTER VIEW public.regional_elo_game_results SET (security_invoker = true);
ALTER VIEW public.global_elo_game_results SET (security_invoker = true);

CREATE OR REPLACE VIEW public.games_ranking_eligible AS
SELECT *, 'ranking'::text AS elo_tier
FROM public.global_elo_game_results
WHERE ranking_eligible;

CREATE OR REPLACE VIEW public.games_local_eligible AS
SELECT *, 'local'::text AS elo_tier
FROM public.global_elo_game_results
WHERE local_eligible;

CREATE OR REPLACE VIEW public.games_all_eligible AS
SELECT *, 'all'::text AS elo_tier
FROM public.global_elo_game_results
WHERE all_eligible;

CREATE OR REPLACE VIEW public.games_elo_tiers AS
SELECT * FROM public.games_ranking_eligible
UNION ALL
SELECT * FROM public.games_local_eligible
UNION ALL
SELECT * FROM public.games_all_eligible;

ALTER VIEW public.games_ranking_eligible SET (security_invoker = true);
ALTER VIEW public.games_local_eligible SET (security_invoker = true);
ALTER VIEW public.games_all_eligible SET (security_invoker = true);
ALTER VIEW public.games_elo_tiers SET (security_invoker = true);

GRANT SELECT ON public.games_ranking_eligible TO anon, authenticated;
GRANT SELECT ON public.games_local_eligible TO anon, authenticated;
GRANT SELECT ON public.games_all_eligible TO anon, authenticated;
GRANT SELECT ON public.games_elo_tiers TO anon, authenticated;
