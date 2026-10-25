-- Migration: Winrate matrix + pod-aware metrics RPCs (#147, #148)
-- Required by: /winrates matrix page (#150) and commander pod-metric badges (#151), both
-- blocked on this migration landing first (see umbrella issue #146).
--
-- Adds three pieces of shared plumbing plus the two public RPCs:
--   1. wilson_ci_95(successes, trials)              -- shared Wilson 95% CI helper
--   2. is_rate_statistically_significant(...)        -- shared significance heuristic
--   3. top_commanders_by_metashare(top_n, days_back)  -- shared top-N-by-metashare cutoff
--   4. get_winrate_matrix(top_n, days_back)           -- #147
--   5. get_pod_metrics(top_n, days_back)              -- #148
--
-- Implementation notes (read before touching):
--
-- * The `commander_matchups` table (20260110000001_initial_schema.sql) is never populated by
--   ingestion (nothing in src/ writes to it -- only the dedup sweep scripts repoint its FKs
--   *if* rows exist). The live `get_commander_matchups` RPC
--   (20260121200000_topdeck_handle_and_matchup_enhancements.sql) does not read from it either;
--   it computes matchups on the fly from game_participants/tournament_entries/tournaments. Both
--   RPCs below follow that same live-computation approach so they return real data and stay
--   consistent with get_commander_matchups, rather than reading from the empty table the issue
--   text pointed at.
-- * get_commander_matchups has no "aggregate" row of its own -- like get_winrate_matrix's
--   pairwise cells, every row it returns is already a per-opponent breakdown. Verified by hand
--   against a seeded fixture: get_winrate_matrix(top_n, days_back)'s pairwise (non-OVERALL,
--   non-mirror) cell for (X, Y) matches get_commander_matchups(X)'s row for opponent Y exactly,
--   whenever days_back covers the same span get_commander_matchups implicitly does (all-time;
--   it has no time-window parameter, so exact reconciliation needs a days_back that covers full
--   history). The OVERALL row (deck_b IS NULL) is a genuinely new metric this migration adds --
--   get_commander_matchups has no equivalent "this commander's total win rate across every
--   opponent" row to reconcile it against.
-- * game_participants.result only distinguishes 'win' / 'draw' / 'loss' / 'bye' -- there is no
--   per-game numeric finish position anywhere in the schema (tournament_entries.final_standing
--   is the *tournament*-level standing, not per-pod). "Top 2" is therefore derived exactly as
--   the issue describes: order participants within a game by result (win, then draw, then
--   loss) and break ties on seat_position ascending, then take the top two of that ordering.
--   See test_supabase_migration_integrity.py / test_winrate_matrix_pod_metrics.py for the
--   fixture that exercises this against all four "which seat won" orderings.

-- ============================================================================
-- 1. Wilson 95% confidence interval helper (shared by both RPCs below)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.wilson_ci_95(
  p_successes bigint,
  p_trials bigint
)
RETURNS TABLE (ci_low numeric, ci_high numeric)
LANGUAGE sql
IMMUTABLE
AS $$
  -- Wilson score interval, z = 1.96 (95% confidence). Reference check:
  -- wins=50, games=100 -> ci_low ~= 0.4039, ci_high ~= 0.5962.
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
  'Shared Wilson 95% CI helper for get_winrate_matrix (#147) and get_pod_metrics (#148). '
  'Always returns exactly one row; ci_low/ci_high are NULL when p_trials <= 0.';

GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO anon;
GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO authenticated;
GRANT EXECUTE ON FUNCTION public.wilson_ci_95(bigint, bigint) TO service_role;

-- ============================================================================
-- 2. Statistical significance heuristic (matches get_commander_matchups' convention)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_rate_statistically_significant(
  p_trials bigint,
  p_observed_rate numeric,
  p_expected_rate numeric DEFAULT 0.25
)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  -- Same tiered games-count/deviation heuristic as get_commander_matchups
  -- (20260121200000_topdeck_handle_and_matchup_enhancements.sql), generalized to accept an
  -- arbitrary expected base rate so get_pod_metrics can key threat_score off 0.25 (P(win) in
  -- a 4-player pod) the same way get_commander_matchups does for its win_rate column.
  SELECT
    CASE
      WHEN p_trials >= 30 THEN TRUE
      WHEN p_trials >= 20 AND ABS(p_observed_rate - p_expected_rate) > 0.10 THEN TRUE
      WHEN p_trials >= 10 AND ABS(p_observed_rate - p_expected_rate) > 0.15 THEN TRUE
      ELSE FALSE
    END;
$$;

GRANT EXECUTE ON FUNCTION public.is_rate_statistically_significant(bigint, numeric, numeric) TO anon;
GRANT EXECUTE ON FUNCTION public.is_rate_statistically_significant(bigint, numeric, numeric) TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_rate_statistically_significant(bigint, numeric, numeric) TO service_role;

-- ============================================================================
-- 3. Shared top-N-by-metashare cutoff (both RPCs must agree on "who's in the matrix")
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
  'Metashare = game participations (excluding byes) within days_back. Shared by '
  'get_winrate_matrix (#147) and get_pod_metrics (#148) so both agree on inclusion.';

GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.top_commanders_by_metashare(integer, integer) TO service_role;

-- ============================================================================
-- 4. get_winrate_matrix -- #147
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
  -- wins, losses, draws, ...). plpgsql's default variable_conflict=error setting means ANY bare
  -- reference to an identifier that also names an OUT parameter raises "ambiguous column
  -- reference", even deep inside a CTE and even when only one relation is in scope -- table-
  -- qualifying the reference is not enough by itself if the *column name* collides. Only the
  -- final SELECT's target list re-introduces the real output names, via AS aliasing.
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
    -- one OVERALL row per top-N deck (deck_b = NULL). See the module header re: reconciling
    -- this with get_commander_matchups, which has no time-window parameter of its own.
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
  'deck_b_commander_id NULL are the mtgdecks-style OVERALL row per deck.';

GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_winrate_matrix(integer, integer) TO service_role;

-- ============================================================================
-- 5. get_pod_metrics -- #148
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_pod_metrics(
  top_n integer DEFAULT 30,
  days_back integer DEFAULT 180
)
RETURNS TABLE (
  commander_id uuid,
  pods_present bigint,
  wins bigint,
  top_two bigint,
  threat_score numeric,
  threat_ci_low numeric,
  threat_ci_high numeric,
  survivability numeric,
  survivability_ci_low numeric,
  survivability_ci_high numeric,
  is_statistically_significant boolean
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  -- NOTE: see the matching comment in get_winrate_matrix -- every intermediate CTE column here
  -- uses an "x_" prefix so nothing collides with an OUT parameter name (commander_id,
  -- pods_present, wins, top_two, ...); plpgsql's variable_conflict=error default turns any such
  -- bare-name collision into "ambiguous column reference", even under table-qualification.
  RETURN QUERY
  WITH x_top AS (
    SELECT t.commander_id AS x_commander_id
    FROM public.top_commanders_by_metashare(top_n, days_back) AS t
  ),
  x_placements AS (
    -- Per-game finish derivation: game_participants.result carries no numeric placement, so
    -- rank within each game by result (win beats draw beats loss) and break ties on
    -- seat_position ascending, exactly as the issue describes. "Top 2" = the best two of that
    -- ranking. See test_winrate_matrix_pod_metrics.py for the fixture covering all four
    -- "which seat won" orderings.
    SELECT
      gp.entry_id AS x_entry_id,
      gp.result AS x_result,
      RANK() OVER (
        PARTITION BY gp.game_id
        ORDER BY
          CASE gp.result WHEN 'win' THEN 0 WHEN 'draw' THEN 1 WHEN 'loss' THEN 2 ELSE 3 END,
          gp.seat_position ASC
      ) AS x_placement
    FROM game_participants gp
    WHERE gp.result <> 'bye'
  ),
  x_pod_metrics AS (
    SELECT
      tea.commander_id AS x_commander_id,
      COUNT(*) AS x_pods_present,
      COUNT(*) FILTER (WHERE pl.x_result = 'win') AS x_wins,
      COUNT(*) FILTER (WHERE pl.x_placement <= 2) AS x_top_two
    FROM x_placements pl
    JOIN tournament_entries tea ON tea.id = pl.x_entry_id
    JOIN tournaments t ON t.id = tea.tournament_id
    WHERE t.start_date >= NOW() - make_interval(days => GREATEST(days_back, 0))
      AND tea.commander_id IN (SELECT x_commander_id FROM x_top)
    GROUP BY tea.commander_id
  )
  SELECT
    pm.x_commander_id AS commander_id,
    pm.x_pods_present AS pods_present,
    pm.x_wins AS wins,
    pm.x_top_two AS top_two,
    ROUND(pm.x_wins::numeric / pm.x_pods_present, 4) AS threat_score,
    threat_ci.ci_low AS threat_ci_low,
    threat_ci.ci_high AS threat_ci_high,
    ROUND(pm.x_top_two::numeric / pm.x_pods_present, 4) AS survivability,
    surv_ci.ci_low AS survivability_ci_low,
    surv_ci.ci_high AS survivability_ci_high,
    -- Matches get_commander_matchups' significance convention, keyed off threat_score
    -- (P(win | at table)) exactly as that RPC keys its own flag off win_rate.
    public.is_rate_statistically_significant(
      pm.x_pods_present,
      pm.x_wins::numeric / pm.x_pods_present,
      0.25
    ) AS is_statistically_significant
  FROM x_pod_metrics pm
  CROSS JOIN LATERAL public.wilson_ci_95(pm.x_wins, pm.x_pods_present) threat_ci
  CROSS JOIN LATERAL public.wilson_ci_95(pm.x_top_two, pm.x_pods_present) surv_ci
  WHERE pm.x_pods_present > 0
  ORDER BY pm.x_commander_id;
END;
$$;

COMMENT ON FUNCTION public.get_pod_metrics(integer, integer) IS
  'Threat score (P(win | at table)) and survivability (P(top-2 | at table)) per top-N '
  'commander, with Wilson 95% CIs (#148). Top-N cutoff shared with get_winrate_matrix (#147) '
  'via top_commanders_by_metashare.';

GRANT EXECUTE ON FUNCTION public.get_pod_metrics(integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.get_pod_metrics(integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_pod_metrics(integer, integer) TO service_role;
