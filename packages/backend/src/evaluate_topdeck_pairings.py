#!/usr/bin/env python3
"""Evaluate TopDeck Swiss pairing approximations against historical pairings."""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ingest import SupabaseClient, load_local_env
from run_historical_tournament_from_round_sim import fetch_round_rows, fetch_seat_map
from run_historical_tournament_sim import (
    build_spec_and_players,
    fetch_active_player_count_from_games,
)
from sim_engine import apply_bye, apply_pod_result, initialize_state
from sim_pairings import (
    _optimize_pods_for_repeats,
    _topdeck_pod_sizes,
    pair_swiss_round,
    sort_standings_rows,
    standings_sort_key,
)
from sim_types import Pod, PodResult, TournamentState


@dataclass(frozen=True)
class HistoricalRound:
    pods: list[Pod]
    results: list[PodResult]
    byes: list[str]


@dataclass(frozen=True)
class PairingCandidate:
    label: str
    samples: int
    builder: Callable[[TournamentState, int, random.Random], list[Pod]]


def log_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def pod_pair_set(pods: list[Pod]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for pod in pods:
        players = sorted(set(pod.player_ids))
        for left_index, player_id in enumerate(players):
            for opponent_id in players[left_index + 1 :]:
                pairs.add((player_id, opponent_id))
    return pairs


def exact_pod_set(pods: list[Pod]) -> set[frozenset[str]]:
    return {frozenset(pod.player_ids) for pod in pods if len(pod.player_ids) >= 2}


def score_pairings(predicted: list[Pod], actual: list[Pod]) -> dict[str, float]:
    predicted_pairs = pod_pair_set(predicted)
    actual_pairs = pod_pair_set(actual)
    pair_hits = len(predicted_pairs & actual_pairs)
    exact_hits = len(exact_pod_set(predicted) & exact_pod_set(actual))
    actual_pods = [pod for pod in actual if len(pod.player_ids) >= 2]
    table_hits = 0
    actual_by_table = {pod.table_number: frozenset(pod.player_ids) for pod in actual_pods}
    for pod in predicted:
        if actual_by_table.get(pod.table_number) == frozenset(pod.player_ids):
            table_hits += 1
    return {
        "pair_recall": pair_hits / len(actual_pairs) if actual_pairs else 0.0,
        "pair_precision": pair_hits / len(predicted_pairs) if predicted_pairs else 0.0,
        "exact_pod_recall": exact_hits / len(actual_pods) if actual_pods else 0.0,
        "table_exact_recall": table_hits / len(actual_pods) if actual_pods else 0.0,
    }


def profile_recall(expected_profiles: list[tuple[Any, ...]], actual_profiles: list[tuple[Any, ...]]) -> float:
    if not actual_profiles:
        return 0.0
    expected_counts = Counter(expected_profiles)
    actual_counts = Counter(actual_profiles)
    hits = sum(min(actual_counts[profile], expected_counts.get(profile, 0)) for profile in actual_counts)
    return hits / len(actual_profiles)


def pod_points_profile(state: TournamentState, pod: Pod) -> tuple[int, ...]:
    return tuple(sorted((state.standings[player_id].points for player_id in pod.player_ids), reverse=True))


def pod_record_profile(state: TournamentState, pod: Pod) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        sorted(
            (
                (
                    state.standings[player_id].points,
                    state.standings[player_id].wins,
                    state.standings[player_id].draws,
                    state.standings[player_id].losses,
                )
                for player_id in pod.player_ids
            ),
            reverse=True,
        )
    )


def expected_points_profiles(state: TournamentState) -> list[tuple[int, ...]]:
    eligible = state.eligible_player_ids
    points: list[int] = []
    for player_id, standing in state.standings.items():
        if eligible is not None and player_id not in eligible:
            continue
        points.append(standing.points)
    points.sort(reverse=True)
    profiles: list[tuple[int, ...]] = []
    start = 0
    for size in _topdeck_pod_sizes(len(points), state.spec.pod_size):
        profiles.append(tuple(points[start : start + size]))
        start += size
    return profiles


def expected_record_profiles(state: TournamentState) -> list[tuple[tuple[int, int, int, int], ...]]:
    eligible = state.eligible_player_ids
    records: list[tuple[int, int, int, int]] = []
    for player_id, standing in state.standings.items():
        if eligible is not None and player_id not in eligible:
            continue
        records.append((standing.points, standing.wins, standing.draws, standing.losses))
    records.sort(reverse=True)
    profiles: list[tuple[tuple[int, int, int, int], ...]] = []
    start = 0
    for size in _topdeck_pod_sizes(len(records), state.spec.pod_size):
        profiles.append(tuple(records[start : start + size]))
        start += size
    return profiles


def score_profile_feasibility(state: TournamentState, actual_pods: list[Pod]) -> dict[str, float]:
    actual_points = [pod_points_profile(state, pod) for pod in actual_pods]
    actual_records = [pod_record_profile(state, pod) for pod in actual_pods]
    return {
        "points_profile_recall": profile_recall(expected_points_profiles(state), actual_points),
        "record_profile_recall": profile_recall(expected_record_profiles(state), actual_records),
    }


def summarize_scores(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {}
    keys = sorted(scores[0])
    summary: dict[str, float] = {}
    for key in keys:
        values = [score[key] for score in scores]
        summary[key] = statistics.fmean(values)
        summary[f"{key}_best"] = max(values)
    return summary


def build_historical_rounds(
    round_rows: list[dict[str, Any]],
    seat_map: dict[tuple[str, str], int],
) -> dict[int, HistoricalRound]:
    grouped: dict[int, dict[tuple[str, int], list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in round_rows:
        round_number = row.get("round_number")
        table_number = row.get("table_number")
        game_id = row.get("game_id")
        if round_number is None or table_number is None or not game_id:
            continue
        grouped[int(round_number)][(str(game_id), int(table_number))].append(row)

    rounds: dict[int, HistoricalRound] = {}
    for round_number, tables in grouped.items():
        pods: list[Pod] = []
        results: list[PodResult] = []
        byes: list[str] = []
        ordered_tables = sorted(tables.items(), key=lambda item: (item[1][0].get("table_number") or 0, item[0][0]))
        for table_index, ((game_id, table_number), rows) in enumerate(ordered_tables, start=1):
            player_ids = [str(row["player_id"]) for row in rows if row.get("player_id")]
            result_values = {str(row.get("result") or "").lower() for row in rows}
            if len(player_ids) == 1 and "bye" in result_values:
                byes.append(player_ids[0])
                continue
            if len(player_ids) < 2:
                continue
            seats_by_player = {
                str(row["player_id"]): seat_map.get((game_id, str(row["entry_id"])), seat)
                for seat, row in enumerate(rows, start=1)
                if row.get("player_id")
            }
            pod = Pod(
                round_index=round_number - 1,
                table_number=int(table_number or table_index),
                player_ids=player_ids,
                round_name=f"Round {round_number}",
                seats_by_player=seats_by_player,
            )
            winner_ids = [str(row["player_id"]) for row in rows if str(row.get("result") or "").lower() == "win"]
            is_draw = "draw" in result_values
            pods.append(pod)
            results.append(
                PodResult(
                    round_index=round_number - 1,
                    table_number=pod.table_number,
                    player_ids=player_ids,
                    is_draw=is_draw,
                    winner_id=None if is_draw else (winner_ids[0] if winner_ids else None),
                    win_probabilities=tuple(),
                    draw_probability=0.0,
                )
            )
        rounds[round_number] = HistoricalRound(pods=pods, results=results, byes=byes)
    return rounds


def _pods_from_ordered_players(player_ids: list[str], round_index: int, pod_size: int) -> list[Pod]:
    pods: list[Pod] = []
    start = 0
    for table_number, size in enumerate(_topdeck_pod_sizes(len(player_ids), pod_size), start=1):
        pod_players = player_ids[start : start + size]
        start += size
        if len(pod_players) < 2:
            continue
        pods.append(
            Pod(
                round_index=round_index,
                table_number=table_number,
                player_ids=pod_players,
                round_name=f"Round {round_index + 1}",
                seats_by_player={player_id: seat for seat, player_id in enumerate(pod_players, start=1)},
            )
        )
    return pods


def build_current_pairing(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    return pair_swiss_round(state, round_index, rng)


def build_exact_record_no_repeat(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    original_threshold = state.spec.repeat_avoidance_max_pods
    state.spec.repeat_avoidance_max_pods = None
    try:
        return pair_swiss_round(state, round_index, rng)
    finally:
        state.spec.repeat_avoidance_max_pods = original_threshold


def build_standings_order(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    del rng
    ordered = [row.player_id for row in sort_standings_rows(state)]
    return _pods_from_ordered_players(ordered, round_index, state.spec.pod_size)


def build_standings_order_repeat(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    del rng
    ordered = [row.player_id for row in sort_standings_rows(state)]
    pod_groups = [pod.player_ids for pod in _pods_from_ordered_players(ordered, round_index, state.spec.pod_size)]
    repeat_avoidance_max_pods = state.spec.repeat_avoidance_max_pods
    if repeat_avoidance_max_pods and len(pod_groups) <= repeat_avoidance_max_pods:
        pod_groups = _optimize_pods_for_repeats(state, pod_groups)
    return [
        Pod(
            round_index=round_index,
            table_number=index,
            player_ids=pod_players,
            round_name=f"Round {round_index + 1}",
            seats_by_player={player_id: seat for seat, player_id in enumerate(pod_players, start=1)},
        )
        for index, pod_players in enumerate(pod_groups, start=1)
    ]


def build_points_seed_order(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    del rng
    eligible = state.eligible_player_ids
    ordered = sorted(
        (
            player_id
            for player_id in state.standings
            if eligible is None or player_id in eligible
        ),
        key=lambda player_id: (
            -state.standings[player_id].points,
            state.players[player_id].tiebreak_seed,
            player_id,
        ),
    )
    return _pods_from_ordered_players(ordered, round_index, state.spec.pod_size)


def build_record_standings_order(state: TournamentState, round_index: int, rng: random.Random) -> list[Pod]:
    del rng
    eligible = state.eligible_player_ids
    ordered = sorted(
        (
            player_id
            for player_id in state.standings
            if eligible is None or player_id in eligible
        ),
        key=lambda player_id: (
            -state.standings[player_id].points,
            -state.standings[player_id].wins,
            -state.standings[player_id].draws,
            state.standings[player_id].losses,
            standings_sort_key(state, player_id),
        ),
    )
    return _pods_from_ordered_players(ordered, round_index, state.spec.pod_size)


def pairing_candidates(samples: int) -> list[PairingCandidate]:
    return [
        PairingCandidate("current_exact_record_random_repeat", samples, build_current_pairing),
        PairingCandidate("exact_record_random_no_repeat", samples, build_exact_record_no_repeat),
        PairingCandidate("standings_order", 1, build_standings_order),
        PairingCandidate("standings_order_repeat", 1, build_standings_order_repeat),
        PairingCandidate("points_seed_order", 1, build_points_seed_order),
        PairingCandidate("record_standings_order", 1, build_record_standings_order),
    ]


def evaluate_round(
    state: TournamentState,
    actual_pods: list[Pod],
    *,
    round_number: int,
    tournament_seed: str,
    samples: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in pairing_candidates(samples):
        candidate_scores = []
        for sample_index in range(candidate.samples):
            rng = random.Random(f"{tournament_seed}:{round_number}:{candidate.label}:{sample_index}")
            predicted = candidate.builder(state, round_number - 1, rng)
            candidate_scores.append(score_pairings(predicted, actual_pods))
        rows.append(
            {
                "candidate": candidate.label,
                "round_number": round_number,
                "actual_pods": len(actual_pods),
                "samples": candidate.samples,
                "metrics": summarize_scores(candidate_scores),
            }
        )
    return rows


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_candidate: dict[str, list[dict[str, float]]] = defaultdict(list)
    by_candidate_round: dict[str, dict[int, list[dict[str, float]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        candidate = str(row["candidate"])
        metrics = dict(row["metrics"])
        by_candidate[candidate].append(metrics)
        by_candidate_round[candidate][int(row["round_number"])].append(metrics)

    aggregate: dict[str, Any] = {}
    for candidate, metric_rows in sorted(by_candidate.items()):
        metric_keys = sorted(metric_rows[0]) if metric_rows else []
        aggregate[candidate] = {
            "rounds": len(metric_rows),
            "average": {
                key: statistics.fmean(row[key] for row in metric_rows)
                for key in metric_keys
            },
            "by_round": {
                str(round_number): {
                    key: statistics.fmean(row[key] for row in round_metric_rows)
                    for key in metric_keys
                }
                for round_number, round_metric_rows in sorted(by_candidate_round[candidate].items())
            },
        }
    return aggregate


def fetch_candidate_tournaments(
    client: SupabaseClient,
    *,
    limit: int,
    candidate_scan_limit: int,
    min_active_player_count: int,
    max_active_player_count: int | None,
    start_date_from: str | None,
    start_date_to: str | None,
) -> list[dict[str, Any]]:
    params = {
        "select": "id,name,start_date,player_count,top_cut",
        "order": "start_date.desc",
        "limit": str(candidate_scan_limit),
    }
    if start_date_from:
        params["start_date"] = f"gte.{start_date_from}"
    if start_date_to:
        params["start_date"] = f"lt.{start_date_to}"
    rows = client.select("tournaments", params, max_retries=8)
    selected: list[dict[str, Any]] = []
    for row in rows:
        active_count = fetch_active_player_count_from_games(client, str(row["id"]))
        if active_count >= min_active_player_count and (
            max_active_player_count is None or active_count <= max_active_player_count
        ):
            selected.append({**row, "active_player_count": active_count})
        if len(selected) >= limit:
            break
    return selected


def evaluate_tournament(
    client: SupabaseClient,
    tournament_id: str,
    *,
    samples: int,
    repeat_avoidance_max_pods: int,
    include_inactive_entries: bool,
) -> dict[str, Any]:
    spec, players, _entries, feature_context = build_spec_and_players(
        client,
        tournament_id,
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        active_players_only=not include_inactive_entries,
    )
    round_rows = fetch_round_rows(client, tournament_id)
    game_ids = sorted({str(row["game_id"]) for row in round_rows if row.get("game_id")})
    seat_map = fetch_seat_map(client, game_ids)
    rounds = build_historical_rounds(round_rows, seat_map)
    state = initialize_state(spec, players, feature_context=feature_context)

    round_results: list[dict[str, Any]] = []
    for round_number in sorted(rounds):
        historical_round = rounds[round_number]
        if historical_round.pods:
            round_results.extend(
                evaluate_round(
                    state,
                    historical_round.pods,
                    round_number=round_number,
                    tournament_seed=spec.tournament_id,
                    samples=samples,
                )
            )
        for result in historical_round.results:
            apply_pod_result(state, result)
        for player_id in historical_round.byes:
            if player_id in state.standings:
                apply_bye(state, player_id)

    return {
        "tournament": {
            "id": spec.tournament_id,
            "name": spec.name,
            "player_count": spec.player_count,
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "rounds": round_results,
        "aggregate": aggregate_rows(round_results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--candidate-scan-limit", type=int, default=50)
    parser.add_argument("--min-active-player-count", type=int, default=32)
    parser.add_argument("--max-active-player-count", type=int)
    parser.add_argument("--start-date-from")
    parser.add_argument("--start-date-to")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--repeat-avoidance-max-pods", type=int, default=32)
    parser.add_argument("--include-inactive-entries", action="store_true")
    parser.add_argument("--output", type=Path, help="Write JSON results to this path instead of stdout.")
    args = parser.parse_args()

    started = time.perf_counter()
    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])

    if args.tournament_id:
        tournaments = [{"id": tournament_id} for tournament_id in args.tournament_id]
    else:
        log_progress("Selecting candidate tournaments...")
        tournaments = fetch_candidate_tournaments(
            client,
            limit=args.limit,
            candidate_scan_limit=args.candidate_scan_limit,
            min_active_player_count=args.min_active_player_count,
            max_active_player_count=args.max_active_player_count,
            start_date_from=args.start_date_from,
            start_date_to=args.start_date_to,
        )
        log_progress(f"Selected {len(tournaments)} tournaments.")

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, tournament in enumerate(tournaments, start=1):
        tournament_id = str(tournament["id"])
        try:
            log_progress(f"[{index}/{len(tournaments)}] Evaluating {tournament_id}...")
            results.append(
                evaluate_tournament(
                    client,
                    tournament_id,
                    samples=args.samples,
                    repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
                    include_inactive_entries=args.include_inactive_entries,
                )
            )
        except Exception as exc:  # pragma: no cover - CLI reporting path
            errors.append({"tournament_id": tournament_id, "error": str(exc)})
            log_progress(f"ERROR {tournament_id}: {exc}")

    all_round_rows = [
        row
        for result in results
        for row in result["rounds"]
    ]
    payload = {
        "config": {
            "samples": args.samples,
            "repeat_avoidance_max_pods": args.repeat_avoidance_max_pods,
            "candidate_scan_limit": args.candidate_scan_limit,
            "min_active_player_count": args.min_active_player_count,
            "max_active_player_count": args.max_active_player_count,
            "start_date_from": args.start_date_from,
            "start_date_to": args.start_date_to,
            "tournament_ids": [str(row["id"]) for row in tournaments],
        },
        "runtime_seconds": time.perf_counter() - started,
        "aggregate": aggregate_rows(all_round_rows),
        "errors": errors,
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log_progress(f"Wrote {args.output}.")
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
