-- Aggregate public leaderboard display counters from the base tables instead
-- of paging the wide global_elo_game_results view through PostgREST. Starting
-- from the requested TopDeck IDs lets the planner use the player, entry, and
-- participant indexes, avoiding the production statement timeout.
CREATE OR REPLACE FUNCTION public.get_elo_display_stats(
  p_topdeck_ids text[],
  p_tier text DEFAULT 'ranking'
)
RETURNS TABLE (
  topdeck_id text,
  games_played integer,
  wins integer,
  draws integer,
  losses integer
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = ''
AS $$
  SELECT
    p.topdeck_id,
    COUNT(*) FILTER (WHERE gp.result IN ('win', 'draw', 'loss'))::integer AS games_played,
    COUNT(*) FILTER (WHERE gp.result = 'win')::integer AS wins,
    COUNT(*) FILTER (WHERE gp.result = 'draw')::integer AS draws,
    COUNT(*) FILTER (WHERE gp.result = 'loss')::integer AS losses
  FROM public.players p
  JOIN public.tournament_entries te ON te.player_id = p.id
  JOIN public.game_participants gp ON gp.entry_id = te.id
  JOIN public.games g ON g.id = gp.game_id
  JOIN public.tournaments t ON t.id = g.tournament_id
  WHERE p.topdeck_id = ANY (p_topdeck_ids)
    AND (
      (p_tier = 'ranking'
        AND t.player_count >= 30
        AND t.start_date::date <= CURRENT_DATE
        AND LOWER(COALESCE(g.status, 'completed')) IN ('completed', 'complete', 'done')
        AND COALESCE(NULLIF(BTRIM(te.decklist_text), ''), NULLIF(BTRIM(te.decklist_url), '')) IS NOT NULL
        AND COALESCE(t.topdeck_tid, '') NOT ILIKE '%league%'
        AND t.name NOT ILIKE '%league%'
        AND t.name NOT ILIKE '%casual%'
        AND t.name NOT ILIKE '%exhibition%'
        AND t.name !~* '(^|[^[:alnum:]_])fun([^[:alnum:]_]|$)')
      OR (p_tier = 'all' AND t.start_date IS NOT NULL)
    )
  GROUP BY p.topdeck_id;
$$;

REVOKE ALL ON FUNCTION public.get_elo_display_stats(text[], text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_elo_display_stats(text[], text) TO anon, authenticated;

COMMENT ON FUNCTION public.get_elo_display_stats(text[], text) IS
  'Returns ranking-eligible or all-game display counts for at most 50 requested TopDeck IDs.';
