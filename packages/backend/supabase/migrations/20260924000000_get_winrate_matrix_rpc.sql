-- Migration: Top-N pairwise commander matchup matrix RPC (#147)
-- Required by: /winrates matrix page (#150), blocked on this migration landing first
-- (see umbrella issue #146). Siblings #148 (pod metrics), #149 (EV per commander) and #151
-- (badges) are expected to build on this RPC's conventions but are NOT implemented here.
--
-- Adds:
--   1. wilson_ci_95(successes, trials)                -- shared Wilson 95% CI helper
--   2. top_commanders_by_metashare(top_n, days_back)   -- top-N-by-metashare cutoff
--   3. get_winrate_matrix(top_n, days_back)            -- #147
--
-- Implementation notes (read before touching):
--
-- * The `commander_matchups` table (20260110000001_initial_schema.sql) is never populated by
--   ingestion -- nothing under packages/backend/src writes new rows into it; only the
--   dedup/consolidation sweeps (sweep_partner_commander_order.py, sweep_ub_alt_name_commander_
--   dedup.py) repoint its two commander FKs *if* rows already exist. Confirmed by grep against
--   current `packages/backend/src`. The live `get_commander_matchups` RPC
--   (20260121100001_commander_matchups_function.sql) does not read from that table either -- it
--   computes matchups on the fly from game_participants/tournament_entries/tournaments.
--   get_winrate_matrix below follows that same live-computation approach so it returns real
--   data and stays reconcilable with get_commander_matchups, instead of reading from a table
--   that is always empty in practice.
-- * get_commander_matchups has no time-window parameter and no filter beyond excluding byes --
--   it is effectively all-time. get_winrate_matrix's *pairwise* (non-OVERALL, non-mirror)
--   cells reconcile exactly against it: for a top-N pair (A, B), get_winrate_matrix's (A, B)
--   row matches get_commander_matchups(A)'s row for opponent B game-for-game, provided
--   days_back covers get_commander_matchups' implicit all-time scope and its p_min_games
--   threshold (default 5) is lowered enough not to hide the pair. Verified by hand against the
--   fixture in test_winrate_matrix_integration.py. To keep that reconciliation exact,
--   get_winrate_matrix mirrors get_commander_matchups' join shape (game_participants/
--   tournament_entries/tournaments only, no completed-status or conflicted-game filtering from
--   the newer games_all_eligible/games_elo_tiers eligibility views added in 20260726000000+).
--   The OVERALL row (deck_b_commander_id IS NULL) has no equivalent in get_commander_matchups
--   to reconcile against -- that RPC counts a commander's games once per *opponent* (so a
--   4-player pod contributes to up to three of its rows), never once per *participation*, so
--   summing its rows for a commander does not equal that commander's total game count. OVERALL
--   is a new metric this migration adds, computed straightforwardly as one row per participation
--   aggregated across the window.
-- * game_participants.result only distinguishes 'win' / 'loss' / 'draw' / 'bye' -- pairwise
--   winrate here is therefore a marginal (P(a wins | a and b both at the table)), not a 1v1
--   duel result. A 4-player pod contributes up to 3 pairwise rows per participation (one per
--   distinct opponent commander present), matching the cEDH-native framing in the umbrella
--   issue (#146).
--
-- Reference Wilson check: wins=50, games=100 -> ci_low ~= 0.4038, ci_high ~= 0.5962. See
-- tests/test_wilson_ci_helper.py for the pure-Python mirror of this formula.

-- ============================================================================
-- 1. Wilson 95% confidence interval helper (shared plumbing for future winrate RPCs)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.wilson_ci_95(
  p_successes bigint,
  p_trials bigint
)
RETURNS TABLE (ci_low numeric, ci_high numeric)
LANGUAGE sql
IMMUTABLE
AS $$
  -- Wilson score interval, z = 1.96 (95% confidence).
  SELECT
    CASE WHEN p_trials > 0 THEN GREATEST(0, ROUND((w.centre - w.margin) / w.denom, 4)) END AS ci_low,
    CASE WHEN p_trials > 0 THEN LEAST(1, ROUND((w.centre + w.margin) / w.denom, 4)) END AS ci_high
  FROM (
    SELECT
      (1 + (1.96 ^ 2) / NULLIF(p_trials, 0)::numeric) AS denom,
      (
        (p_successes::numeric / NULLIF(p_trials, 0))
        + (1.96 ^ 2) / (2 * NULLIF(p_trials, 0)::numeric)
      ) AS centre,
      (
        1.96 * sqrt(
          GREATEST(
            0,
            (p_successes::numeric / NULLIF(p_trials, 0))
              * (1 - (p_successes::numeric / NULLIF(p_trials, 0)))
              / NULLIF(p_trials, 0)::numeric
            + (1.96 ^ 2) / (4 * NULLIF(p_trials, 0)::numeric ^ 2)
          )
        )
      ) AS margin
  ) w;
$$;

COMMENT ON FUNCTION public.wilson_ci_95(bigint, bigint) IS
  'Shared Wilson 95% CI helper, first used by get_winrate_matrix (#147). Always returns '
  'exactly one row; ci_low/ci_high are NULL when p_trials <= 0.';

GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO anon;
GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO authenticated;
GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO service_role;

-- ============================================================================
-- 2. Top-N-by-metashare cutoff (kept as its own function so future winrate-family
--    RPCs, e.g. #148/#149, can share the same "who's in scope" definition)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.top_commanders_by_metashare(
  p_top_n integer DEFAULT 30,
  p_days_back integer DEFAULT 180
)
RETURNS TABLE (commander_id uuid, games_played bigint)
LANGUAGE sql
STABLE
AS $$
  SELECT
    te.commander_id,
    COUNT(*) AS games_played
  FROM game_participants gp
  JOIN tournament_entries te ON te.id = gp.entry_id
  JOIN tournaments t ON t.id = te.tournament_id
  WHERE gp.result <> 'bye'
    AND t.start_date >= NOW() - make_interval(days => GREATEST(p_days_back, 0))
  GROUP BY te.commander_id
  ORDER BY games_played DESC, te.commander_id
  LIMIT GREATEST(p_top_n, 0);
$$;

COMMENT ON FUNCTION public.top_commanders_by_metashare(integer, integer) IS
  'Metashare = game participations (excluding byes) within days_back. Used by '
  'get_winrate_matrix (#147) to determine which commanders enter the matrix.';

GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO service_role;

-- ============================================================================
-- 3. get_winrate_matrix -- #147
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_winrate_matrix(
  top_n integer DEFAULT 30,
  days_back integer DEFAULT 180
)
RETURNS TABLE (
  deck_a_commander_id uuid,
  deck_b_commander_id uuid,
  games_played bigint,
  wins bigint,
  losses bigint,
  draws bigint,
  point_winrate numeric,
  ci_low numeric,
  ci_high numeric
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  -- NOTE: every intermediate CTE column below is deliberately named with an "x_" prefix, never
  -- reusing an OUT-parameter name (deck_a_commander_id, deck_b_commander_id, games_played,
  -- wins, losses, draws, ...). plpgsql's default variable_conflict=error setting turns any bare
  -- reference to an identifier that also names an OUT parameter into "ambiguous column
  -- reference", even inside a CTE and even when only one relation is in scope -- the final
  -- SELECT's target list is the only place the real output names are reintroduced, via AS.
  RETURN QUERY
  WITH x_top AS (
    SELECT t.commander_id AS x_commander_id, t.games_played AS x_top_games
    FROM public.top_commanders_by_metashare(top_n, days_back) AS t
  ),
  x_window_games AS (
    -- One row per (deck_a participation, deck_b co-participant) pair, restricted to games
    -- within the window and to top-N decks on both sides. A 4-player pod contributes up to 3
    -- such pairwise rows per participation (one per opponent commander present) -- pairwise
    -- winrate here is a marginal (P(a wins | a and b both at the table)), not a 1v1 duel
    -- result, matching the umbrella issue's (#146) cEDH-specific framing.
    SELECT
      tea.commander_id AS x_a_commander_id,
      teb.commander_id AS x_b_commander_id,
      a.result AS x_a_result
    FROM game_participants a
    JOIN tournament_entries tea ON tea.id = a.entry_id
    JOIN tournaments t ON t.id = tea.tournament_id
    JOIN game_participants b ON b.game_id = a.game_id AND b.id <> a.id
    JOIN tournament_entries teb ON teb.id = b.entry_id
    WHERE a.result <> 'bye'
      AND b.result <> 'bye'
      AND t.start_date >= NOW() - make_interval(days => GREATEST(days_back, 0))
      AND tea.commander_id <> teb.commander_id
      AND tea.commander_id IN (SELECT x_commander_id FROM x_top)
      AND teb.commander_id IN (SELECT x_commander_id FROM x_top)
  ),
  x_pairwise AS (
    SELECT
      x_a_commander_id,
      x_b_commander_id,
      COUNT(*) AS x_games,
      COUNT(*) FILTER (WHERE x_a_result = 'win') AS x_wins,
      COUNT(*) FILTER (WHERE x_a_result = 'loss') AS x_losses,
      COUNT(*) FILTER (WHERE x_a_result = 'draw') AS x_draws
    FROM x_window_games
    GROUP BY x_a_commander_id, x_b_commander_id
  ),
  x_mirror AS (
    -- mtgdecks.net convention: a deck vs itself is always exactly 50%, at the deck's full
    -- window sample size (there's no literal self-vs-self pod to aggregate).
    SELECT
      x_commander_id AS x_a_commander_id,
      x_commander_id AS x_b_commander_id,
      x_top_games AS x_games,
      ROUND(x_top_games / 2.0)::bigint AS x_wins,
      (x_top_games - ROUND(x_top_games / 2.0)::bigint) AS x_losses,
      0::bigint AS x_draws
    FROM x_top
    WHERE x_top_games > 0
  ),
  x_overall AS (
    -- Per-deck aggregate across every opponent within the window (not just top-N opponents),
    -- one OVERALL row per top-N deck (deck_b = NULL). This is the mtgdecks-style sortable
    -- headline winrate column; unlike the pairwise cells it does not restrict opponents to
    -- the top-N set. It has no reconciliation partner in get_commander_matchups -- see the
    -- module header for why (that RPC counts per-opponent, not per-participation).
    SELECT
      tea.commander_id AS x_a_commander_id,
      NULL::uuid AS x_b_commander_id,
      COUNT(*) AS x_games,
      COUNT(*) FILTER (WHERE a.result = 'win') AS x_wins,
      COUNT(*) FILTER (WHERE a.result = 'loss') AS x_losses,
      COUNT(*) FILTER (WHERE a.result = 'draw') AS x_draws
    FROM game_participants a
    JOIN tournament_entries tea ON tea.id = a.entry_id
    JOIN tournaments t ON t.id = tea.tournament_id
    WHERE a.result <> 'bye'
      AND t.start_date >= NOW() - make_interval(days => GREATEST(days_back, 0))
      AND tea.commander_id IN (SELECT x_commander_id FROM x_top)
    GROUP BY tea.commander_id
  ),
  x_combined AS (
    SELECT * FROM x_pairwise
    UNION ALL
    SELECT * FROM x_mirror
    UNION ALL
    SELECT * FROM x_overall
  )
  SELECT
    c.x_a_commander_id AS deck_a_commander_id,
    c.x_b_commander_id AS deck_b_commander_id,
    c.x_games AS games_played,
    c.x_wins AS wins,
    c.x_losses AS losses,
    c.x_draws AS draws,
    -- Mirror cells are forced to exactly 0.5000 regardless of games_played's parity (the
    -- wins/losses split above is an even/odd approximation for display only) -- required by
    -- the "mirror cells return exactly 50%" acceptance criterion on #147.
    CASE
      WHEN c.x_a_commander_id = c.x_b_commander_id THEN 0.5::numeric
      ELSE ROUND(c.x_wins::numeric / c.x_games, 4)
    END AS point_winrate,
    ci.ci_low,
    ci.ci_high
  FROM x_combined c
  CROSS JOIN LATERAL public.wilson_ci_95(c.x_wins, c.x_games) ci
  WHERE c.x_games > 0
  ORDER BY c.x_a_commander_id, c.x_b_commander_id NULLS FIRST;
END;
$$;

COMMENT ON FUNCTION public.get_winrate_matrix(integer, integer) IS
  'Top-N pairwise commander matchup matrix with Wilson 95% CIs (#147). Rows with '
  'deck_b_commander_id NULL are the mtgdecks-style OVERALL row per deck. Empty cells (no '
  'games) are omitted, never returned with a null winrate. Returns at most '
  'top_n * (top_n + 1) rows (pairwise + mirror + OVERALL, minus any empty cells).';

GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO service_role;
