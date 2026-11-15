"""Unit tests for the meta-share-weighted EV math added for #149
(``get_commander_meta_ev``, see
``supabase/migrations/20261115010000_commander_meta_ev_rpc.sql``).

This reimplements the migration's per-deck weighting and sparsity fallback in pure Python so the
issue's acceptance scenario -- "a deck winning 80% vs a rare archetype and 30% vs the dominant
one should resolve to EV ~= 30%, not an inflated number from overweighting the rare matchup" --
can be checked without a live Postgres instance (the CI ``unittest discover`` step has none; see
``.github/workflows/ci-backend.yml``). ``MigrationSqlMatchesReferenceMathTests`` ties this
reference implementation to the deployed SQL text so the two can't silently drift apart.
"""

import math
import unittest
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "supabase" / "migrations"
META_EV_MIGRATION = MIGRATIONS_DIR / "20261115010000_commander_meta_ev_rpc.sql"


def _clamp(value: float, low: float = 0.01, high: float = 0.99) -> float:
    return min(high, max(low, value))


def _geometric_mean(values: list[float]) -> float:
    return math.exp(sum(math.log(_clamp(v)) for v in values) / len(values))


def compute_meta_ev(
    triples: list[tuple[tuple[str, ...], str]],
    pairwise_matrix: dict[tuple[str, str], tuple[float, float, float]],
    min_triple_obs: int = 10,
) -> dict[str, float]:
    """Pure-Python mirror of get_commander_meta_ev's per-commander aggregation.

    ``triples`` is a list of (opponent_triple, result) pairs for ONE focal commander's
    participations, where opponent_triple is a tuple of the (up to three) opposing commander
    ids and result is "win" or "loss" (draws are a loss for this simplified EV, matching the
    SQL's ``x_focal_result = 'win'`` filter). ``pairwise_matrix`` maps
    (focal_commander, opponent_commander) -> (point_winrate, ci_low, ci_high), mirroring
    get_winrate_matrix's pairwise cells for this focal commander.
    """
    grouped: dict[tuple[str, ...], dict[str, int]] = {}
    for triple, result in triples:
        key = tuple(sorted(triple))
        bucket = grouped.setdefault(key, {"pods": 0, "wins": 0})
        bucket["pods"] += 1
        if result == "win":
            bucket["wins"] += 1

    total_pods = sum(b["pods"] for b in grouped.values())
    weighted_ev = 0.0
    weighted_ci_low = 0.0
    weighted_ci_high = 0.0
    direct_pods = 0

    for triple, bucket in grouped.items():
        pods, wins = bucket["pods"], bucket["wins"]
        if pods >= min_triple_obs:
            winrate = wins / pods
            # CI bound doesn't matter for these tests beyond being present; use the point
            # estimate's own neighborhood as a stand-in (the real SQL uses wilson_ci_95).
            ci_low, ci_high = winrate, winrate
            direct_pods += pods
        else:
            marginals = [pairwise_matrix.get((None, opp), (0.25, 0.1, 0.4)) for opp in triple]
            winrate = _geometric_mean([m[0] for m in marginals])
            ci_low = _geometric_mean([m[1] for m in marginals])
            ci_high = _geometric_mean([m[2] for m in marginals])

        weighted_ev += pods * winrate
        weighted_ci_low += pods * ci_low
        weighted_ci_high += pods * ci_high

    return {
        "meta_ev": weighted_ev / total_pods,
        "meta_ev_ci_low": weighted_ci_low / total_pods,
        "meta_ev_ci_high": weighted_ci_high / total_pods,
        "composition_coverage": direct_pods / total_pods,
    }


class MetaEvSparsityFallbackReorderTests(unittest.TestCase):
    """#149 acceptance criterion: a deck's EV should track the realistic (frequent) matchup,
    not be inflated by a rare-but-favorable one."""

    def test_rare_favorable_matchup_does_not_inflate_ev_toward_naive_average(self) -> None:
        # Deck X: 90 pods against the dominant archetype D (30% winrate, directly observed --
        # clears min_triple_obs), 10 pods against a rare archetype R (80% winrate, but each
        # individual triple containing R is unique/near-unique in a large field, so it falls
        # back to the pairwise marginal rather than ever accumulating >= min_triple_obs on its
        # own triple key).
        dominant_triple = ("D", "D", "D")
        rare_triple = ("R", "D", "D")

        # The rare triple's own count (9) is deliberately one below min_triple_obs (10) so it
        # exercises the fallback path instead of ever being counted direct.
        triples = [(dominant_triple, "win" if i < 27 else "loss") for i in range(90)]  # 27/90 = 0.30
        triples += [(rare_triple, "win" if i < 7 else "loss") for i in range(9)]  # < min_triple_obs

        pairwise_matrix = {
            (None, "D"): (0.30, 0.22, 0.39),
            (None, "R"): (0.80, 0.60, 0.92),
        }

        result = compute_meta_ev(triples, pairwise_matrix, min_triple_obs=10)

        naive_average = (0.30 + 0.80) / 2  # the "inflated" number the issue warns against
        self.assertLess(result["meta_ev"], naive_average)
        # Close to the dominant/realistic matchup's winrate, not a 50/50 blend with the rare one.
        self.assertAlmostEqual(result["meta_ev"], 0.30, delta=0.08)

    def test_composition_coverage_is_not_hardcoded_to_one(self) -> None:
        dominant_triple = ("D", "D", "D")
        rare_triple = ("R", "D", "D")
        triples = [(dominant_triple, "win" if i < 27 else "loss") for i in range(90)]
        triples += [(rare_triple, "win" if i < 7 else "loss") for i in range(9)]
        pairwise_matrix = {(None, "D"): (0.30, 0.22, 0.39), (None, "R"): (0.80, 0.60, 0.92)}

        result = compute_meta_ev(triples, pairwise_matrix, min_triple_obs=10)

        # 90 of 99 pods are the directly-observed dominant triple; the rare triple (9 pods,
        # below min_triple_obs) falls back instead of counting toward coverage.
        self.assertAlmostEqual(result["composition_coverage"], 90 / 99, places=4)
        self.assertLess(result["composition_coverage"], 1.0)
        self.assertGreater(result["composition_coverage"], 0.0)

    def test_fully_direct_coverage_when_every_triple_clears_the_floor(self) -> None:
        triple = ("D", "D", "D")
        triples = [(triple, "win" if i < 12 else "loss") for i in range(40)]

        result = compute_meta_ev(triples, {(None, "D"): (0.30, 0.2, 0.4)}, min_triple_obs=10)

        self.assertEqual(result["composition_coverage"], 1.0)
        self.assertAlmostEqual(result["meta_ev"], 0.30, places=4)

    def test_zero_coverage_not_none_when_every_triple_is_a_fallback(self) -> None:
        """Regression test (Codex review on PR #384): when *every* triple a commander faced is
        individually sparse (below min_triple_obs), the SQL's
        ``SUM(...) FILTER (WHERE x_is_direct)`` matches zero rows and -- unlike this Python
        mirror's plain running total, which starts at 0 -- a SQL FILTER-aggregate over zero
        matching rows is NULL, not 0. Without an explicit COALESCE around that SUM in the
        migration, composition_coverage would come back NULL for such a commander, violating
        CommanderMetaEvSchema's non-nullable contract. This test pins the *intended* value (an
        honest 0.0) so a regression in the SQL shows up via the migration-text assertion in
        MigrationSqlMatchesReferenceMathTests below, even though this particular Python
        reimplementation can't reproduce the NULL-vs-zero bug itself.
        """
        # Every individual triple below min_triple_obs=10 -> composition_coverage must be 0.0.
        triples = [(("D", "D", "R"), "win" if i < 3 else "loss") for i in range(8)]
        triples += [(("E", "E", "F"), "win" if i < 1 else "loss") for i in range(5)]
        pairwise_matrix = {(None, "D"): (0.3, 0.2, 0.4), (None, "R"): (0.3, 0.2, 0.4)}

        result = compute_meta_ev(triples, pairwise_matrix, min_triple_obs=10)

        self.assertEqual(result["composition_coverage"], 0.0)
        self.assertIsNotNone(result["composition_coverage"])


class GeometricMeanFallbackClampingTests(unittest.TestCase):
    def test_geometric_mean_of_three_average_matchups_does_not_collapse_toward_zero(self) -> None:
        # A raw product of three ~0.3 marginals would be 0.027 -- not usable as a winrate. The
        # geometric mean instead stays close to the marginals themselves.
        mean = _geometric_mean([0.30, 0.30, 0.30])
        self.assertAlmostEqual(mean, 0.30, places=4)

    def test_zero_percent_marginal_is_clamped_before_taking_log(self) -> None:
        # Should not raise (math domain error) and should not force the blend to exactly 0.
        mean = _geometric_mean([0.0, 0.5, 0.5])
        self.assertGreater(mean, 0.0)

    def test_hundred_percent_marginal_is_clamped_before_taking_log(self) -> None:
        mean = _geometric_mean([1.0, 0.5, 0.5])
        self.assertLess(mean, 1.0)


class MigrationSqlMatchesReferenceMathTests(unittest.TestCase):
    """Ties the Python reference implementation above to the deployed SQL text."""

    def test_signature_matches_issue_spec_plus_documented_min_triple_obs_extension(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        self.assertIn(
            "CREATE OR REPLACE FUNCTION public.get_commander_meta_ev(\n"
            "  top_n integer DEFAULT 30,\n"
            "  days_back integer DEFAULT 180,\n"
            "  min_triple_obs integer DEFAULT 10\n"
            ")",
            sql,
        )
        self.assertIn(
            "RETURNS TABLE (\n"
            "  commander_id uuid,\n"
            "  meta_ev numeric,\n"
            "  meta_ev_ci_low numeric,\n"
            "  meta_ev_ci_high numeric,\n"
            "  composition_coverage numeric\n"
            ")",
            sql,
        )

    def test_uses_geometric_mean_fallback_not_a_raw_product(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("EXP(AVG(LN(LEAST(GREATEST(COALESCE(m.point_winrate, 0.25), 0.01), 0.99))))", sql)
        self.assertIn("min_triple_obs", sql)

    def test_depends_on_get_winrate_matrix_for_pairwise_marginals(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("FROM public.get_winrate_matrix(top_n, days_back)", sql)

    def test_grants_execute_to_public_postgrest_roles(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        for role in ("anon", "authenticated", "service_role"):
            self.assertIn(
                f"GRANT EXECUTE ON FUNCTION public.get_commander_meta_ev(integer, integer, integer) TO {role};",
                sql,
            )

    def test_documents_the_composition_probability_model_choice(self) -> None:
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("empirical", sql.lower())
        self.assertIn("composition_coverage", sql)
        self.assertIn("not hardcoded to 1.0", sql)

    def test_composition_coverage_coalesces_the_all_fallback_case_to_zero(self) -> None:
        """Codex review finding on PR #384: without this COALESCE, a commander whose every
        triple is a fallback (none individually clears min_triple_obs) gets a NULL
        composition_coverage instead of 0, because SUM(...) FILTER(...) over zero matching rows
        is NULL in SQL -- see test_zero_coverage_not_none_when_every_triple_is_a_fallback above
        for the pure-Python pin of the intended (non-NULL) value."""
        sql = META_EV_MIGRATION.read_text()

        self.assertIn(
            "COALESCE(SUM(tev.x_triple_pods) FILTER (WHERE tev.x_is_direct), 0)::numeric",
            sql,
        )

    def test_window_excludes_future_dated_tournaments(self) -> None:
        """Codex review finding on PR #384: matches the upper-bound convention from
        20260815000000_exclude_future_dated_tournaments.sql (a 2030-dated TopDeck practice
        event that previously contaminated other unbounded windows)."""
        sql = META_EV_MIGRATION.read_text()

        self.assertIn("AND t.start_date::date <= CURRENT_DATE", sql)


if __name__ == "__main__":
    unittest.main()
