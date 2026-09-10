"""Integration test for get_winrate_matrix / get_pod_metrics (#147, #148) against a real Postgres.

CI's unit-test step (``python -m unittest discover packages/backend/tests``, see
``.github/workflows/ci-backend.yml``) runs without a database connection, so this test is
opt-in: it skips cleanly unless both an optional driver and a target database are available,
per the repo's "Optional Dependency Detection" convention (see AGENTS.md) --

    uv run python -m unittest packages.backend.tests.test_winrate_matrix_pod_metrics_integration

To run it locally against `supabase start`'s local Postgres (port 54322 by default) or any
throwaway Postgres with the migrations replayed:

    CEDH_TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \\
      uv run python -m unittest packages.backend.tests.test_winrate_matrix_pod_metrics_integration

This exact fixture (and these exact expected values) were run by hand against a local
Postgres 16 during development of #147/#148; see the migration's module header for the
reconciliation notes that scenario proved out.
"""

import os
import sys
import unittest

DATABASE_URL = os.environ.get("CEDH_TEST_DATABASE_URL")

# Another test module in this suite (test_rebuild_global_elo_tables.py) sets
# sys.modules["psycopg2"] = None at import time, to exercise supabase_client's ImportError
# fallback path, and never restores it -- a pre-existing test-isolation gap, unrelated to
# #147/#148. That sentinel makes both importlib.util.find_spec("psycopg2") and a plain
# `import psycopg2` report "unavailable" for every module discovered afterward in the same
# process, even when psycopg2 is genuinely installed (Python's documented behavior for a None
# entry in sys.modules). Drop the sentinel (and any already-cached submodule entries, e.g.
# "psycopg2.extras" from an earlier successful import elsewhere -- leaving those cached would
# have `import psycopg2.extras` skip re-attaching .extras onto the freshly re-imported package
# below) before our own check, so this module isn't at the mercy of unittest discover's file
# ordering.
_psycopg2_module_names = [name for name in sys.modules if name == "psycopg2" or name.startswith("psycopg2.")]
if any(sys.modules.get(name) is None for name in _psycopg2_module_names):
    for name in _psycopg2_module_names:
        del sys.modules[name]

try:
    import psycopg2
    import psycopg2.extras

    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

FIXTURE_SQL = """
BEGIN;
INSERT INTO commanders (id, name, commander_names) VALUES
  ('00000000-0000-0000-0000-00000000000a', 'Alpha', ARRAY['Alpha']),
  ('00000000-0000-0000-0000-00000000000b', 'Beta', ARRAY['Beta']),
  ('00000000-0000-0000-0000-00000000000c', 'Gamma', ARRAY['Gamma']),
  ('00000000-0000-0000-0000-00000000000d', 'Delta', ARRAY['Delta']),
  ('00000000-0000-0000-0000-00000000000e', 'Echo', ARRAY['Echo'])
ON CONFLICT (id) DO NOTHING;

INSERT INTO players (id, topdeck_id, name) VALUES
  ('00000000-0000-0000-0000-000000000101', 'wmpm-p1', 'Player1'),
  ('00000000-0000-0000-0000-000000000102', 'wmpm-p2', 'Player2'),
  ('00000000-0000-0000-0000-000000000103', 'wmpm-p3', 'Player3'),
  ('00000000-0000-0000-0000-000000000104', 'wmpm-p4', 'Player4'),
  ('00000000-0000-0000-0000-000000000105', 'wmpm-p5', 'Player5')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tournaments (id, topdeck_tid, name, start_date, player_count, swiss_rounds) VALUES
  ('00000000-0000-0000-0000-0000000000f1', 'wmpm-t01', 'Fixture Cup', NOW() - INTERVAL '10 days', 32, 6)
ON CONFLICT (id) DO NOTHING;

INSERT INTO tournament_entries (id, tournament_id, player_id, commander_id) VALUES
  ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-0000000000f1',
   '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-00000000000a'),
  ('00000000-0000-0000-0000-000000000202', '00000000-0000-0000-0000-0000000000f1',
   '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-00000000000b'),
  ('00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-0000000000f1',
   '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-00000000000c'),
  ('00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-0000000000f1',
   '00000000-0000-0000-0000-000000000104', '00000000-0000-0000-0000-00000000000d'),
  ('00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-0000000000f1',
   '00000000-0000-0000-0000-000000000105', '00000000-0000-0000-0000-00000000000e')
ON CONFLICT (id) DO NOTHING;

INSERT INTO games (id, tournament_id, round_number, status, is_draw) VALUES
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-0000000000f1', 1, 'Completed', false),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-0000000000f1', 2, 'Completed', false),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-0000000000f1', 3, 'Completed', false),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-0000000000f1', 4, 'Completed', false),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-0000000000f1', 5, 'Completed', true),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-0000000000f1', 6, 'Completed', false)
ON CONFLICT (id) DO NOTHING;

INSERT INTO game_participants (game_id, entry_id, seat_position, result, points_earned) VALUES
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000201', 0, 'win', 5),
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000202', 1, 'loss', 0),
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000203', 2, 'loss', 0),
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000204', 3, 'loss', 0),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000202', 0, 'win', 5),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000201', 1, 'loss', 0),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000203', 2, 'loss', 0),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000204', 3, 'loss', 0),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000201', 0, 'win', 5),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000203', 1, 'loss', 0),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000202', 2, 'loss', 0),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000204', 3, 'loss', 0),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000203', 0, 'win', 5),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000204', 1, 'loss', 0),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000201', 2, 'loss', 0),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000202', 3, 'loss', 0),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000201', 0, 'draw', 1),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000202', 1, 'draw', 1),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000203', 2, 'draw', 1),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000204', 3, 'draw', 1),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000205', 0, 'win', 5),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000201', 1, 'loss', 0),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000202', 2, 'loss', 0),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000204', 3, 'loss', 0)
ON CONFLICT DO NOTHING;
COMMIT;
"""

CLEANUP_SQL = """
DELETE FROM game_participants WHERE game_id IN (
  '00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000302',
  '00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000304',
  '00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000306'
);
DELETE FROM games WHERE tournament_id = '00000000-0000-0000-0000-0000000000f1';
DELETE FROM tournament_entries WHERE tournament_id = '00000000-0000-0000-0000-0000000000f1';
DELETE FROM tournaments WHERE id = '00000000-0000-0000-0000-0000000000f1';
DELETE FROM players WHERE id IN (
  '00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000102',
  '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000104',
  '00000000-0000-0000-0000-000000000105'
);
DELETE FROM commanders WHERE id IN (
  '00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-00000000000b',
  '00000000-0000-0000-0000-00000000000c', '00000000-0000-0000-0000-00000000000d',
  '00000000-0000-0000-0000-00000000000e'
);
"""


@unittest.skipUnless(PSYCOPG2_AVAILABLE, "psycopg2 not installed")
@unittest.skipUnless(DATABASE_URL, "set CEDH_TEST_DATABASE_URL to run against a real Postgres")
class WinrateMatrixAndPodMetricsIntegrationTests(unittest.TestCase):
    """Hand-verified fixture: see the migration's module header for the by-hand derivation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = psycopg2.connect(DATABASE_URL)
        cls.conn.autocommit = True
        with cls.conn.cursor() as cur:
            cur.execute(FIXTURE_SQL)

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.conn.cursor() as cur:
            cur.execute(CLEANUP_SQL)
        cls.conn.close()

    def _rows(self, query: str, params: tuple) -> list[dict]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def test_winrate_matrix_matches_hand_computed_fixture(self) -> None:
        rows = self._rows("SELECT * FROM public.get_winrate_matrix(%s, %s)", (4, 365))
        by_pair = {
            (str(r["deck_a_commander_id"]), r["deck_b_commander_id"] and str(r["deck_b_commander_id"])): r for r in rows
        }

        a = "00000000-0000-0000-0000-00000000000a"
        b = "00000000-0000-0000-0000-00000000000b"

        # Row bound: N*(N+1) for N=30 per #147; here N=4 so bound is 20, and this fixture hits
        # it exactly (every pair co-occurred at least once).
        self.assertEqual(len(rows), 20)

        pairwise_ab = by_pair[(a, b)]
        self.assertEqual(pairwise_ab["games_played"], 6)
        self.assertEqual(pairwise_ab["wins"], 2)
        self.assertEqual(float(pairwise_ab["point_winrate"]), 0.3333)

        mirror_a = by_pair[(a, a)]
        self.assertEqual(float(mirror_a["point_winrate"]), 0.5)
        self.assertEqual(mirror_a["games_played"], 6)

        overall_a = by_pair[(a, None)]
        self.assertEqual(overall_a["games_played"], 6)
        self.assertEqual(overall_a["wins"], 2)

    def test_winrate_matrix_reconciles_with_get_commander_matchups(self) -> None:
        a = "00000000-0000-0000-0000-00000000000a"
        matrix_rows = self._rows(
            "SELECT * FROM public.get_winrate_matrix(%s, %s) "
            "WHERE deck_a_commander_id = %s "
            "AND deck_b_commander_id IS NOT NULL "
            "AND deck_b_commander_id != deck_a_commander_id",
            (4, 365, a),
        )
        matchup_rows = self._rows(
            "SELECT * FROM get_commander_matchups(%s, %s, %s, %s)",
            (a, 50, 0, 0),
        )
        matchups_by_opponent = {str(r["opponent_commander_id"]): r for r in matchup_rows}

        for row in matrix_rows:
            opponent = str(row["deck_b_commander_id"])
            matchup = matchups_by_opponent[opponent]
            self.assertEqual(row["games_played"], matchup["games_played"])
            self.assertEqual(row["wins"], matchup["wins"])
            self.assertEqual(row["losses"], matchup["losses"])
            self.assertEqual(row["draws"], matchup["draws"])

    def test_pod_metrics_matches_hand_computed_fixture(self) -> None:
        rows = self._rows("SELECT * FROM public.get_pod_metrics(%s, %s)", (4, 365))
        by_commander = {str(r["commander_id"]): r for r in rows}

        a = by_commander["00000000-0000-0000-0000-00000000000a"]
        self.assertEqual(a["pods_present"], 6)
        self.assertEqual(a["wins"], 2)
        self.assertEqual(a["top_two"], 5)
        self.assertEqual(float(a["threat_score"]), 0.3333)
        self.assertEqual(float(a["survivability"]), 0.8333)

        d = by_commander["00000000-0000-0000-0000-00000000000d"]
        self.assertEqual(d["pods_present"], 6)
        self.assertEqual(d["wins"], 0)
        self.assertEqual(d["top_two"], 1)

    def test_top_n_cutoff_matches_between_both_rpcs(self) -> None:
        matrix_ids = {
            str(r["deck_a_commander_id"])
            for r in self._rows("SELECT DISTINCT deck_a_commander_id FROM public.get_winrate_matrix(%s, %s)", (4, 365))
        }
        pod_ids = {
            str(r["commander_id"])
            for r in self._rows("SELECT commander_id FROM public.get_pod_metrics(%s, %s)", (4, 365))
        }

        self.assertEqual(matrix_ids, pod_ids)
        self.assertNotIn("00000000-0000-0000-0000-00000000000e", matrix_ids)  # excluded by metashare cutoff


if __name__ == "__main__":
    unittest.main()
