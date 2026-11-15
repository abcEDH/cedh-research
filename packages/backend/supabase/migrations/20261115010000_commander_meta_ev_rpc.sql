-- Migration: Meta-share-weighted expected value (EV) per commander (#149)
-- Required by: /winrates matrix page's EV column (#150) and the META EV badge on
-- commanders/[id] (#151). Depends on #147's get_winrate_matrix and shared helpers landing
-- first (20261115000000_winrate_matrix_and_pod_metrics_rpc.sql).
--
-- EV(deck) = Σ over observed pod-compositions  P(composition) × winrate(deck | composition)
--
-- Meta assumption used here (documented per #149's acceptance criteria): a "composition" is
-- the unordered triple of the *other* three commanders a deck's pilot actually sat across from
-- in a completed 4-player pod. P(composition) is estimated empirically and *per-deck*: for
-- each top-N commander D, it is the fraction of D's own observed pods that had exactly that
-- opponent triple (triple_pods / total pods D appeared in). This is the natural reading of
-- "observed pod-compositions" for a single deck's expected performance -- it is not a global
-- composition probability over the whole field, because winrate(deck | composition) is only
-- defined for compositions the deck actually faced. Pods with a bye (fewer than 4 real
-- participants) are excluded; there is no well-defined 3-opponent triple for them.
--
-- Sparsity fallback. Most individual opponent triples are unique or near-unique in a large
-- field (this is a 4-of-many-decks combinatorial space), so most triples will not independently
-- clear `min_triple_obs` (default 10) observations. When a triple has fewer observations than
-- that floor, this migration falls back to combining the deck's *pairwise* marginal winrates
-- against each of the triple's (up to three) opponents, sourced from get_winrate_matrix(top_n,
-- days_back). The combination is a **geometric mean** of the three pairwise point_winrates
-- (equivalently: the cube root of their product) rather than a raw product -- a raw product of
-- three independent probabilities collapses toward zero for any deck with three merely-average
-- matchups (e.g. 0.3 * 0.3 * 0.3 = 0.027), which is not a usable winrate estimate. The geometric
-- mean keeps the fallback bounded in a sane range while still being "a product of pairwise
-- marginals" in the literal, normalized sense (the issue's suggested implementation plan
-- explicitly leaves the exact composition-probability model to be decided and documented here).
-- An opponent missing from the top-N pairwise matrix (e.g. a rarely-played archetype outside
-- top_n) falls back further to the 4-player baseline of 0.25 for that one opponent only.
-- Pairwise rates and CI bounds are clamped to [0.01, 0.99] before the geometric mean so a
-- 0% or 100% marginal can't force the blended estimate to exactly 0 or send the log-mean to
-- -infinity.
--
-- CI propagation: ci_low/ci_high are the same triple_pods-weighted average as the point
-- estimate, using each triple's own Wilson CI when direct (>= min_triple_obs observations) or
-- the geometric mean of the matrix's pairwise CI bounds when using the fallback. This is an
-- approximation (it is not a rigorously re-derived interval for the blended estimator) but
-- keeps the reported band consistent with, and no narrower than what the underlying pairwise
-- data would suggest -- composition_coverage (below) tells the caller how much of the EV rests
-- on direct observation vs this approximation.
--
-- composition_coverage = (pods whose triple independently cleared min_triple_obs) / total pods
-- for that deck. This is a genuine, deck-specific fraction -- not hardcoded to 1.0 -- and will
-- typically be well under 1.0 for most decks, since most individual triples are sparse; the UI
-- can use it to flag low-coverage EVs. See tests/test_commander_meta_ev.py for the fixture
-- demonstrating composition_coverage varies and the reorder/deflation acceptance scenario (a
-- deck winning 80% against a rare archetype and 30% against the dominant one resolves close to
-- 30%, not an inflated blend of the two).

CREATE OR REPLACE FUNCTION public.get_commander_meta_ev(
  top_n integer DEFAULT 30,
  days_back integer DEFAULT 180,
  min_triple_obs integer DEFAULT 10
)
RETURNS TABLE (
  commander_id uuid,
  meta_ev numeric,
  meta_ev_ci_low numeric,
  meta_ev_ci_high numeric,
  composition_coverage numeric,
  -- EV-eligible pod count for *this* commander: only pods with exactly 4 real (non-bye)
  -- participants ever reach x_focal below, which is strictly narrower than get_pod_metrics'
  -- pods_present (that RPC counts every non-bye participation, 4-player or not). The frontend
  -- badge for meta_ev must use this count, not get_pod_metrics' pods_present, or it understates
  -- how sparse the EV estimate actually is (e.g. 90 three-player + 10 four-player pods would
  -- otherwise borrow N=100 from get_pod_metrics when only 10 pods fed this EV).
  pods_present bigint,
  -- Self-contained significance flag using the same shared heuristic and 0.25 baseline as
  -- get_pod_metrics' threat_score, but keyed off *this* RPC's own N and point estimate rather
  -- than borrowed from get_pod_metrics (which can disagree on N -- see pods_present above).
  is_statistically_significant boolean
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  -- NOTE: see the matching comment in get_winrate_matrix -- every intermediate CTE column here
  -- uses an "x_" prefix so nothing collides with an OUT parameter name (commander_id, meta_ev,
  -- ...). plpgsql's variable_conflict=error default turns any bare-name collision into
  -- "ambiguous column reference", even deep inside a CTE.
  RETURN QUERY
  WITH x_top AS (
    SELECT t.commander_id AS x_commander_id
    FROM public.top_commanders_by_metashare(top_n, days_back) AS t
  ),
  x_window_games AS (
    -- Every non-bye participation within the window, tagged with its game and commander.
    -- Pod-size filtering happens next, *before* restricting to top-N focal commanders, so a
    -- pod's real size is never distorted by which of its four decks happen to be top-N.
    SELECT
      gp.game_id AS x_game_id,
      gp.entry_id AS x_entry_id,
      gp.result AS x_result,
      tea.commander_id AS x_commander_id
    FROM game_participants gp
    JOIN tournament_entries tea ON tea.id = gp.entry_id
    JOIN tournaments t ON t.id = tea.tournament_id
    WHERE gp.result <> 'bye'
      -- Future-dated-tournament and top-N-by-metashare conventions mirror
      -- top_commanders_by_metashare (20261115000000_winrate_matrix_and_pod_metrics_rpc.sql) --
      -- see 20260815000000_exclude_future_dated_tournaments.sql for the upper bound's history.
      AND t.start_date::date <= CURRENT_DATE
      AND t.start_date >= NOW() - make_interval(days => GREATEST(days_back, 0))
  ),
  x_pod_sizes AS (
    SELECT x_game_id, COUNT(*) AS x_pod_size
    FROM x_window_games
    GROUP BY x_game_id
  ),
  x_focal AS (
    -- The focal deck's participation in each of its full (4-real-participant) pods.
    SELECT w.x_game_id, w.x_entry_id, w.x_commander_id AS x_focal_commander_id, w.x_result AS x_focal_result
    FROM x_window_games w
    JOIN x_pod_sizes ps ON ps.x_game_id = w.x_game_id
    WHERE ps.x_pod_size = 4
      AND w.x_commander_id IN (SELECT x_commander_id FROM x_top)
  ),
  x_opponents AS (
    -- Grouped by the focal entry_id (not just game_id + commander_id): two different pilots in
    -- the same pod can play the same top-N commander (a mirror seat), and each of those two
    -- participations must keep its own result and its own 3-opponent triple rather than being
    -- collapsed together.
    SELECT
      f.x_game_id,
      f.x_entry_id,
      f.x_focal_commander_id,
      f.x_focal_result,
      w2.x_commander_id AS x_opponent_commander_id
    FROM x_focal f
    JOIN x_window_games w2 ON w2.x_game_id = f.x_game_id AND w2.x_entry_id <> f.x_entry_id
  ),
  x_triples AS (
    SELECT
      x_game_id,
      x_entry_id,
      x_focal_commander_id,
      x_focal_result,
      array_agg(x_opponent_commander_id ORDER BY x_opponent_commander_id) AS x_triple_key
    FROM x_opponents
    GROUP BY x_game_id, x_entry_id, x_focal_commander_id, x_focal_result
  ),
  x_triple_stats AS (
    SELECT
      x_focal_commander_id,
      x_triple_key,
      COUNT(*) AS x_triple_pods,
      COUNT(*) FILTER (WHERE x_focal_result = 'win') AS x_triple_wins
    FROM x_triples
    GROUP BY x_focal_commander_id, x_triple_key
  ),
  x_matrix AS (
    -- Pairwise marginals to blend for the sparsity fallback below. Only non-mirror,
    -- non-OVERALL cells are usable here -- see get_winrate_matrix's module header.
    SELECT deck_a_commander_id, deck_b_commander_id, point_winrate, ci_low, ci_high
    FROM public.get_winrate_matrix(top_n, days_back)
    WHERE deck_b_commander_id IS NOT NULL
      AND deck_a_commander_id <> deck_b_commander_id
  ),
  x_triple_fallback AS (
    SELECT
      ts.x_focal_commander_id,
      ts.x_triple_key,
      -- Geometric mean (= exp(average of logs)) of each opponent's pairwise marginal, clamped
      -- to [0.01, 0.99] so neither a 0%/100% marginal nor a missing opponent (defaulted to the
      -- 0.25 baseline) can force a degenerate log(0).
      EXP(AVG(LN(LEAST(GREATEST(COALESCE(m.point_winrate, 0.25), 0.01), 0.99)))) AS x_fallback_winrate,
      EXP(AVG(LN(LEAST(GREATEST(COALESCE(m.ci_low, 0.1), 0.01), 0.99)))) AS x_fallback_ci_low,
      EXP(AVG(LN(LEAST(GREATEST(COALESCE(m.ci_high, 0.4), 0.01), 0.99)))) AS x_fallback_ci_high
    FROM x_triple_stats ts
    CROSS JOIN LATERAL unnest(ts.x_triple_key) AS x_opp(opponent_commander_id)
    LEFT JOIN x_matrix m
      ON m.deck_a_commander_id = ts.x_focal_commander_id
      AND m.deck_b_commander_id = x_opp.opponent_commander_id
    GROUP BY ts.x_focal_commander_id, ts.x_triple_key
  ),
  x_triple_ev AS (
    SELECT
      ts.x_focal_commander_id,
      ts.x_triple_pods,
      (ts.x_triple_pods >= min_triple_obs) AS x_is_direct,
      CASE
        WHEN ts.x_triple_pods >= min_triple_obs THEN ts.x_triple_wins::numeric / ts.x_triple_pods
        ELSE tf.x_fallback_winrate
      END AS x_triple_winrate,
      CASE WHEN ts.x_triple_pods >= min_triple_obs THEN wci.ci_low ELSE tf.x_fallback_ci_low END AS x_triple_ci_low,
      CASE WHEN ts.x_triple_pods >= min_triple_obs THEN wci.ci_high ELSE tf.x_fallback_ci_high END AS x_triple_ci_high
    FROM x_triple_stats ts
    JOIN x_triple_fallback tf
      ON tf.x_focal_commander_id = ts.x_focal_commander_id
      AND tf.x_triple_key = ts.x_triple_key
    CROSS JOIN LATERAL public.wilson_ci_95(ts.x_triple_wins, ts.x_triple_pods) wci
  ),
  x_commander_ev AS (
    SELECT
      tev.x_focal_commander_id AS x_commander_id,
      SUM(tev.x_triple_pods) AS x_total_pods,
      SUM(tev.x_triple_pods * tev.x_triple_winrate) / NULLIF(SUM(tev.x_triple_pods), 0) AS x_meta_ev,
      SUM(tev.x_triple_pods * tev.x_triple_ci_low) / NULLIF(SUM(tev.x_triple_pods), 0) AS x_meta_ev_ci_low,
      SUM(tev.x_triple_pods * tev.x_triple_ci_high) / NULLIF(SUM(tev.x_triple_pods), 0) AS x_meta_ev_ci_high,
      -- COALESCE guards the case where *every* triple for this commander is a fallback (none
      -- independently cleared min_triple_obs): the FILTER then matches zero rows, and
      -- SUM(...) FILTER(...) over zero rows is NULL, not 0 -- without the COALESCE that NULL
      -- would propagate into composition_coverage and violate the "always a real number"
      -- contract (CommanderMetaEvSchema in apps/web/src/lib/schemas/api-contracts.ts), rendering
      -- as "--" on the matrix/badges instead of the correct 0%.
      COALESCE(SUM(tev.x_triple_pods) FILTER (WHERE tev.x_is_direct), 0)::numeric
        / NULLIF(SUM(tev.x_triple_pods), 0) AS x_composition_coverage
    FROM x_triple_ev tev
    GROUP BY tev.x_focal_commander_id
  )
  SELECT
    x_commander_id AS commander_id,
    ROUND(x_meta_ev, 4) AS meta_ev,
    ROUND(x_meta_ev_ci_low, 4) AS meta_ev_ci_low,
    ROUND(x_meta_ev_ci_high, 4) AS meta_ev_ci_high,
    ROUND(x_composition_coverage, 4) AS composition_coverage,
    x_total_pods AS pods_present,
    public.is_rate_statistically_significant(x_total_pods, x_meta_ev, 0.25) AS is_statistically_significant
  FROM x_commander_ev
  WHERE x_total_pods > 0
  ORDER BY x_commander_id;
END;
$$;

COMMENT ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) IS
  'Meta-share-weighted expected pod winrate per top-N commander (#149): EV = sum over the '
  'deck''s observed opponent-triple compositions of P(triple) * winrate(deck | triple). '
  'Triples with fewer than min_triple_obs observations fall back to the geometric mean of '
  'pairwise marginals from get_winrate_matrix. composition_coverage is the fraction of a '
  'deck''s pods whose triple cleared min_triple_obs directly (not hardcoded to 1.0). '
  'pods_present is this RPC''s own EV-eligible (exactly-4-player-pod) count -- callers must '
  'use it, not get_pod_metrics'' pods_present, for this RPC''s own N/confidence, since '
  'get_pod_metrics counts every non-bye participation regardless of pod size and can '
  'overstate how sparse a given commander''s EV estimate actually is.';

GRANT EXECUTE ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) TO service_role;
