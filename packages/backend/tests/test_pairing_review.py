import unittest
from unittest.mock import MagicMock, patch

from test_pairing_score_profiles import make_state

import evaluate_topdeck_pairings as evaluation
import pairing_history_client as history
from sim_types import Pod


def rows(game_id="g", table=1, players=("p1", "p2", "p3", "p4")):
    return [
        {
            "game_id": game_id,
            "entry_id": pid,
            "player_id": pid,
            "round_number": 1,
            "table_number": table,
            "result": "win" if i == 0 else "loss",
        }
        for i, pid in enumerate(players)
    ]


class PairingReviewTests(unittest.TestCase):
    def test_identical_table_copies_count_only_once(self):
        result = history.build_historical_rounds(rows("a") + rows("b"), {})[1]
        self.assertEqual(len(result.pods), 1)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].winner_id, "p1")

    def test_conflicting_tables_or_repeated_players_abort(self):
        for extra in [rows("b", table=2), rows("b", players=("p1", "p5", "p6", "p7"))]:
            with self.assertRaises(ValueError):
                history.build_historical_rounds(rows("a") + extra, {})

    def test_pending_table_excludes_whole_incomplete_round(self):
        games = [
            {"id": "a", "status": "Completed", "round_number": 1},
            {"id": "b", "status": "Active", "round_number": 2},
            {"id": "c", "status": "Completed", "round_number": 2},
        ]
        source = rows("a") + [dict(row, round_number=2) for row in rows("b") + rows("c")]
        with (
            patch.object(history, "fetch_all", return_value=games),
            patch.object(history, "fetch_raw_round_rows", return_value=source),
        ):
            self.assertEqual(history.fetch_round_rows(object(), "event"), rows("a"))

    def test_missing_winner_is_not_replayed_as_loss(self):
        source = [dict(row, result="loss") for row in rows()]
        with self.assertRaises(ValueError):
            history.build_historical_rounds(source, {})

    def test_date_query_keeps_lower_and_upper_bounds(self):
        client = MagicMock()
        query = client.table.return_value
        for method in ["select", "order", "gte", "lt", "limit"]:
            getattr(query, method).return_value = query
        query.execute.return_value.data = []
        evaluation.fetch_candidate_tournaments(
            client,
            limit=10,
            candidate_scan_limit=20,
            min_active_player_count=4,
            max_active_player_count=None,
            start_date_from="2026-01-01",
            start_date_to="2026-04-01",
        )
        query.gte.assert_called_once_with("start_date", "2026-01-01")
        query.lt.assert_called_once_with("start_date", "2026-04-01")

    def test_current_round_eligibility_excludes_dropped_players(self):
        state = make_state()
        round_ = history.build_historical_rounds(rows(), {})[1]
        history.set_round_eligibility(state, round_)
        self.assertEqual(state.eligible_player_ids, {"p1", "p2", "p3", "p4"})
        for candidate in evaluation.pairing_candidates(1):
            import random

            predicted = candidate.builder(state, 0, random.Random(1))
            self.assertEqual({pid for pod in predicted for pid in pod.player_ids}, state.eligible_player_ids)
        self.assertEqual(evaluation.score_profile_feasibility(state, round_.pods)["record_profile_recall"], 1)

    def test_unequal_pod_sizes_order_fewer_losses_first(self):
        state = make_state()
        state.eligible_player_ids = {f"p{i}" for i in range(1, 8)}
        for i in range(1, 8):
            state.standings[f"p{i}"].losses = i
        pods = [
            Pod(round_index=0, table_number=1, player_ids=[f"p{i}" for i in range(1, 5)]),
            Pod(round_index=0, table_number=2, player_ids=[f"p{i}" for i in range(5, 8)]),
        ]
        self.assertEqual(evaluation.score_profile_feasibility(state, pods)["record_profile_recall"], 1)

    def test_audit_is_report_only(self):
        from audit_topdeck_pairings import build_arg_parser

        with self.assertRaises(SystemExit):
            build_arg_parser().parse_args(["--apply-dedupe"])
