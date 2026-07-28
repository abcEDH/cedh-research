#!/usr/bin/env python3
"""Diagnose how historical pairings differ from strict score-bucket chunking."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evaluate_topdeck_pairings import (
    build_historical_rounds,
    expected_points_profiles,
    expected_record_profiles,
    fetch_candidate_tournaments,
    pod_points_profile,
    pod_record_profile,
    profile_recall,
)
from ingest import SupabaseClient, load_local_env
from run_historical_tournament_from_round_sim import fetch_round_rows, fetch_seat_map
from run_historical_tournament_sim import build_spec_and_players
from sim_engine import apply_bye, apply_pod_result, initialize_state
from sim_types import Pod, TournamentState


POINT_BANDS = (0, 1, 4, 5, 6, 10)


def log_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def size_bucket(player_count: int) -> str:
    if player_count < 40:
        return "small"
    if player_count < 96:
        return "medium"
    return "large"


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def can_form_profile(pool: list[int], profile: tuple[int, ...]) -> bool:
    pool_counts = Counter(pool)
    profile_counts = Counter(profile)
    return all(pool_counts[point] >= count for point, count in profile_counts.items())


def local_neighbor_profile_recall(
    expected_profiles: list[tuple[int, ...]],
    actual_pods: list[Pod],
    state: TournamentState,
    *,
    radius: int,
) -> float:
    if not actual_pods:
        return 0.0
    hits = 0
    for pod_index, pod in enumerate(sorted(actual_pods, key=lambda pod: pod.table_number)):
        profile = pod_points_profile(state, pod)
        left = max(0, pod_index - radius)
        right = min(len(expected_profiles), pod_index + radius + 1)
        pool = [point for expected_profile in expected_profiles[left:right] for point in expected_profile]
        if can_form_profile(pool, profile):
            hits += 1
    return hits / len(actual_pods)


def repeat_pair_count(state: TournamentState, pod: Pod) -> int:
    repeats = 0
    for left_index, player_id in enumerate(pod.player_ids):
        for opponent_id in pod.player_ids[left_index + 1 :]:
            pair = tuple(sorted((player_id, opponent_id)))
            if state.feature_context.tournament_pair_meetings.get(pair, 0) > 0:
                repeats += 1
    return repeats


def round_diagnostics(state: TournamentState, actual_pods: list[Pod]) -> dict[str, Any]:
    expected_points = expected_points_profiles(state)
    expected_records = expected_record_profiles(state)
    actual_points = [pod_points_profile(state, pod) for pod in actual_pods]
    actual_records = [pod_record_profile(state, pod) for pod in actual_pods]
    point_ranges = [
        (max(profile) - min(profile)) if profile else 0
        for profile in actual_points
    ]
    repeat_counts = [repeat_pair_count(state, pod) for pod in actual_pods]
    actual_players = {player_id for pod in actual_pods for player_id in pod.player_ids}
    eligible = state.eligible_player_ids or set(state.standings)
    return {
        "actual_pods": len(actual_pods),
        "actual_player_count": len(actual_players),
        "expected_player_count": len(eligible),
        "actual_players_missing_from_state": len(actual_players - set(state.standings)),
        "state_players_missing_from_actual_round": len(set(eligible) - actual_players),
        "points_profile_recall": profile_recall(expected_points, actual_points),
        "record_profile_recall": profile_recall(expected_records, actual_records),
        "neighbor_radius_1_recall": local_neighbor_profile_recall(expected_points, actual_pods, state, radius=1),
        "neighbor_radius_2_recall": local_neighbor_profile_recall(expected_points, actual_pods, state, radius=2),
        "average_point_range": mean([float(value) for value in point_ranges]),
        "max_point_range": max(point_ranges) if point_ranges else 0,
        "average_repeat_pairs": mean([float(value) for value in repeat_counts]),
        "pods_with_repeat_pair_rate": mean([1.0 if value > 0 else 0.0 for value in repeat_counts]),
        **{
            f"within_{band}_points_rate": mean([1.0 if value <= band else 0.0 for value in point_ranges])
            for band in POINT_BANDS
        },
    }


def tournament_ids_from_evaluation_json(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        str(result["tournament"]["id"])
        for result in payload.get("results") or []
        if (result.get("tournament") or {}).get("id")
    ]


def evaluate_tournament(
    client: SupabaseClient,
    tournament_id: str,
    *,
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

    rows: list[dict[str, Any]] = []
    for round_number in sorted(rounds):
        historical_round = rounds[round_number]
        if historical_round.pods:
            rows.append(
                {
                    "round_number": round_number,
                    **round_diagnostics(state, historical_round.pods),
                }
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
            "size_bucket": size_bucket(spec.player_count),
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "rounds": rows,
    }


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric_keys = [
        "points_profile_recall",
        "record_profile_recall",
        "neighbor_radius_1_recall",
        "neighbor_radius_2_recall",
        "average_point_range",
        "max_point_range",
        "average_repeat_pairs",
        "pods_with_repeat_pair_rate",
        "actual_players_missing_from_state",
        "state_players_missing_from_actual_round",
        *(f"within_{band}_points_rate" for band in POINT_BANDS),
    ]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    groups["all"] = rows
    for row in rows:
        groups[f"size:{row['size_bucket']}"].append(row)
        groups[f"size_round:{row['size_bucket']}:{row['round_number']}"].append(row)

    aggregate: dict[str, Any] = {}
    for group, group_rows in sorted(groups.items()):
        aggregate[group] = {"event_rounds": len(group_rows)}
        for key in metric_keys:
            aggregate[group][key] = mean([float(row[key]) for row in group_rows if row.get(key) is not None])
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", action="append", default=[])
    parser.add_argument("--from-evaluation-json", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--candidate-scan-limit", type=int, default=1000)
    parser.add_argument("--min-active-player-count", type=int, default=16)
    parser.add_argument("--max-active-player-count", type=int)
    parser.add_argument("--start-date-from")
    parser.add_argument("--start-date-to")
    parser.add_argument("--repeat-avoidance-max-pods", type=int, default=32)
    parser.add_argument("--include-inactive-entries", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    started = time.perf_counter()
    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])

    if args.tournament_id:
        tournament_ids = [str(tournament_id) for tournament_id in args.tournament_id]
    elif args.from_evaluation_json:
        tournament_ids = tournament_ids_from_evaluation_json(args.from_evaluation_json)
        log_progress(f"Loaded {len(tournament_ids)} tournament ids from {args.from_evaluation_json}.")
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
        tournament_ids = [str(tournament["id"]) for tournament in tournaments]
        log_progress(f"Selected {len(tournament_ids)} tournaments.")

    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, tournament_id in enumerate(tournament_ids, start=1):
        try:
            if index == 1 or index % 25 == 0:
                log_progress(f"[{index}/{len(tournament_ids)}] Evaluating {tournament_id}...")
            results.append(
                evaluate_tournament(
                    client,
                    tournament_id,
                    repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
                    include_inactive_entries=args.include_inactive_entries,
                )
            )
        except Exception as exc:  # pragma: no cover - CLI reporting path
            errors.append({"tournament_id": tournament_id, "error": str(exc)})
            log_progress(f"ERROR {tournament_id}: {exc}")

    flat_rows = [
        {
            "tournament_id": result["tournament"]["id"],
            "tournament_name": result["tournament"]["name"],
            "player_count": result["tournament"]["player_count"],
            "size_bucket": result["tournament"]["size_bucket"],
            **row,
        }
        for result in results
        for row in result["rounds"]
    ]
    payload = {
        "config": {
            "tournament_count": len(tournament_ids),
            "from_evaluation_json": str(args.from_evaluation_json) if args.from_evaluation_json else None,
            "limit": args.limit,
            "candidate_scan_limit": args.candidate_scan_limit,
            "min_active_player_count": args.min_active_player_count,
            "max_active_player_count": args.max_active_player_count,
            "start_date_from": args.start_date_from,
            "start_date_to": args.start_date_to,
        },
        "runtime_seconds": time.perf_counter() - started,
        "aggregate": aggregate_rows(flat_rows),
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
