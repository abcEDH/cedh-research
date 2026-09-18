#!/usr/bin/env python3
"""Backtest the resume-state tournament simulator across historical tournaments."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from statistics import mean
from typing import Any

from ingest import load_local_env
from run_historical_tournament_from_round_sim import build_round_structures, fetch_round_rows, fetch_seat_map
from run_historical_tournament_sim import (
    DEFAULT_DRAW_MODEL_PATH,
    build_spec_and_players,
    derive_top_cut_player_ids,
)
from sim_engine import apply_pod_result, initialize_state, run_monte_carlo_from_state
from sim_models import load_draw_model_artifact
from supabase import Client
from supabase_client import get_supabase_client


def fetch_candidate_tournaments(
    client: Client,
    *,
    limit: int,
    min_player_count: int,
    start_date_from: str | None,
    start_date_to: str | None,
) -> list[dict[str, Any]]:
    query = (
        client.table("tournaments")
        .select("id,name,start_date,player_count,top_cut")
        .gt("top_cut", 0)
        .gte("player_count", min_player_count)
    )
    if start_date_from:
        query = query.gte("start_date", start_date_from)
    if start_date_to:
        query = query.lt("start_date", start_date_to)
    return query.order("start_date", desc=True).limit(limit).execute().data


def build_state_after_completed_rounds(
    client: Client,
    tournament_id: str,
    completed_rounds: int,
):
    spec, players, entries, feature_context = build_spec_and_players(client, tournament_id)
    round_rows = fetch_round_rows(client, tournament_id)
    game_ids = sorted({str(row["game_id"]) for row in round_rows if row.get("game_id")})
    seat_map = fetch_seat_map(client, game_ids)
    rounds = build_round_structures(round_rows, seat_map)

    if completed_rounds < 0 or completed_rounds > spec.swiss_rounds:
        raise ValueError(f"Invalid completed_rounds={completed_rounds} for swiss_rounds={spec.swiss_rounds}")

    state = initialize_state(spec, players, feature_context=feature_context)
    for round_number in range(1, completed_rounds + 1):
        pods, results = rounds[round_number]
        for result in results:
            apply_pod_result(state, result)
    state.current_round_index = completed_rounds
    return spec, players, entries, rounds, state


def compute_actual_round_draw_rates(
    rounds: dict[int, tuple[list[Any], list[Any]]],
    *,
    completed_rounds: int,
    swiss_rounds: int,
) -> dict[int, float]:
    rates: dict[int, float] = {}
    for round_number in range(completed_rounds + 1, swiss_rounds + 1):
        pods, results = rounds.get(round_number, ([], []))
        if not results:
            continue
        draw_count = sum(1 for result in results if result.is_draw)
        rates[round_number] = draw_count / len(results)
    return rates


def brier_score(probabilities: dict[str, float], actual_positive_ids: set[str], all_player_ids: list[str]) -> float:
    if not all_player_ids:
        return 0.0
    total = 0.0
    for player_id in all_player_ids:
        predicted = float(probabilities.get(player_id, 0.0))
        actual = 1.0 if player_id in actual_positive_ids else 0.0
        total += (predicted - actual) ** 2
    return total / len(all_player_ids)


def top_cut_overlap(probabilities: dict[str, float], actual_top_cut_ids: set[str], cut_size: int) -> int:
    predicted = {
        player_id for player_id, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:cut_size]
    }
    return len(predicted & actual_top_cut_ids)


def evaluate_checkpoint(
    client: Client,
    draw_model,
    *,
    tournament_id: str,
    completed_rounds: int,
    simulations: int,
    seed: int,
    workers: int | None,
    lock_next_round: bool,
) -> dict[str, Any]:
    spec, players, entries, rounds, state = build_state_after_completed_rounds(client, tournament_id, completed_rounds)
    locked_round_pods = None
    if lock_next_round:
        locked_round_pods = rounds.get(completed_rounds + 1, (None, None))[0]

    summary = run_monte_carlo_from_state(
        state,
        draw_model,
        simulations=simulations,
        seed=seed,
        workers=workers,
        start_round_index=completed_rounds,
        locked_round_pods=locked_round_pods,
    ).to_dict()

    player_ids = [player.player_id for player in players]
    actual_top_cut_ids = derive_top_cut_player_ids(entries, spec.top_cut)
    actual_winner_id = next((str(row["player_id"]) for row in entries if row.get("final_standing") == 1), None)
    actual_round_draw_rates = compute_actual_round_draw_rates(
        rounds,
        completed_rounds=completed_rounds,
        swiss_rounds=spec.swiss_rounds,
    )

    win_probabilities = summary["win_probability"]
    top_cut_probabilities = summary["top_cut_probability"]
    actual_winner_probability = float(win_probabilities.get(actual_winner_id or "", 0.0))
    winner_log_loss = -math.log(max(actual_winner_probability, 1e-9))

    simulated_round_draw_rates = {
        int(round_number): float(rate) for round_number, rate in summary["round_draw_rate"].items()
    }
    common_rounds = sorted(set(actual_round_draw_rates) & set(simulated_round_draw_rates))
    round_draw_rate_mae = (
        mean(
            abs(actual_round_draw_rates[round_number] - simulated_round_draw_rates[round_number])
            for round_number in common_rounds
        )
        if common_rounds
        else None
    )

    return {
        "tournament": {
            "id": spec.tournament_id,
            "name": spec.name,
            "player_count": spec.player_count,
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "checkpoint": {
            "completed_rounds": completed_rounds,
            "remaining_rounds": max(0, spec.swiss_rounds - completed_rounds),
            "locked_next_round": bool(locked_round_pods),
        },
        "metrics": {
            "actual_winner_probability": actual_winner_probability,
            "winner_log_loss": winner_log_loss,
            "top_cut_brier": brier_score(top_cut_probabilities, actual_top_cut_ids, player_ids),
            "top_cut_overlap": top_cut_overlap(top_cut_probabilities, actual_top_cut_ids, spec.top_cut),
            "round_draw_rate_mae": round_draw_rate_mae,
        },
        "actual": {
            "winner_id": actual_winner_id,
            "top_cut_count": len(actual_top_cut_ids),
            "round_draw_rate": actual_round_draw_rates,
        },
        "simulated": {
            "round_draw_rate": simulated_round_draw_rates,
        },
        "simulations": simulations,
    }


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"cases": 0}
    metric_lists: dict[str, list[float]] = defaultdict(list)
    for result in results:
        for name, value in result["metrics"].items():
            if value is not None:
                metric_lists[name].append(float(value))
    return {
        "cases": len(results),
        "average_metrics": {name: mean(values) for name, values in metric_lists.items() if values},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-player-count", type=int, default=128)
    parser.add_argument("--start-date-from")
    parser.add_argument("--start-date-to")
    parser.add_argument("--checkpoint-rounds", nargs="+", type=int, default=[4, 5, 6])
    parser.add_argument("--lock-next-round", action="store_true")
    parser.add_argument("--tournament-id", action="append", dest="tournament_ids")
    args = parser.parse_args()

    load_local_env()
    client = get_supabase_client(url=os.environ["SUPABASE_URL"], key=os.environ["SUPABASE_SERVICE_KEY"])
    draw_model = load_draw_model_artifact(args.draw_model_path)

    if args.tournament_ids:
        tournaments = [{"id": tournament_id} for tournament_id in args.tournament_ids]
    else:
        tournaments = fetch_candidate_tournaments(
            client,
            limit=args.limit,
            min_player_count=args.min_player_count,
            start_date_from=args.start_date_from,
            start_date_to=args.start_date_to,
        )

    results: list[dict[str, Any]] = []
    for tournament in tournaments:
        tournament_id = str(tournament["id"])
        try:
            spec, _, _, _, _ = build_state_after_completed_rounds(client, tournament_id, 0)
        except Exception as exc:  # pragma: no cover - CLI reporting path
            results.append({"tournament": {"id": tournament_id}, "error": str(exc)})
            continue

        valid_checkpoints = sorted(
            checkpoint for checkpoint in args.checkpoint_rounds if 0 <= checkpoint < spec.swiss_rounds
        )
        for checkpoint in valid_checkpoints:
            case_seed = args.seed + len(results) * 10_000 + checkpoint
            try:
                results.append(
                    evaluate_checkpoint(
                        client,
                        draw_model,
                        tournament_id=tournament_id,
                        completed_rounds=checkpoint,
                        simulations=args.simulations,
                        seed=case_seed,
                        workers=args.workers,
                        lock_next_round=args.lock_next_round,
                    )
                )
            except Exception as exc:  # pragma: no cover - CLI reporting path
                results.append(
                    {
                        "tournament": {"id": tournament_id, "name": spec.name},
                        "checkpoint": {"completed_rounds": checkpoint},
                        "error": str(exc),
                    }
                )

    successful_results = [result for result in results if "metrics" in result]
    output = {
        "config": {
            "simulations": args.simulations,
            "workers": args.workers,
            "limit": args.limit,
            "min_player_count": args.min_player_count,
            "checkpoint_rounds": args.checkpoint_rounds,
            "lock_next_round": args.lock_next_round,
        },
        "aggregate": aggregate_results(successful_results),
        "results": results,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
