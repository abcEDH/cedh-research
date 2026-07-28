#!/usr/bin/env python3
"""Evaluate whether historical pods match deterministic score-bucket profiles."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from evaluate_topdeck_pairings import (
    build_historical_rounds,
    fetch_candidate_tournaments,
    score_profile_feasibility,
)
from ingest import SupabaseClient, load_local_env
from run_historical_tournament_from_round_sim import fetch_round_rows, fetch_seat_map
from run_historical_tournament_sim import build_spec_and_players
from sim_engine import apply_bye, apply_pod_result, initialize_state


def log_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def size_bucket(player_count: int) -> str:
    if player_count < 40:
        return "small"
    if player_count < 96:
        return "medium"
    return "large"


def average(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return statistics.fmean(values) if values else None


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    groups["all"] = rows
    for row in rows:
        groups[f"size:{row['size_bucket']}"].append(row)
        groups[f"size_round:{row['size_bucket']}:{row['round_number']}"].append(row)
    return {
        group: {
            "event_rounds": len(group_rows),
            "points_profile_recall": average(group_rows, "points_profile_recall"),
            "record_profile_recall": average(group_rows, "record_profile_recall"),
        }
        for group, group_rows in sorted(groups.items())
    }


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
                    "actual_pods": len(historical_round.pods),
                    **score_profile_feasibility(state, historical_round.pods),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", action="append", default=[])
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
            if index == 1 or index % 25 == 0:
                log_progress(f"[{index}/{len(tournaments)}] Evaluating {tournament_id}...")
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
