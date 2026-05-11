#!/usr/bin/env python3
"""Backtest full historical tournament simulations across draw models."""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from ingest import SupabaseClient, load_local_env
from run_historical_tournament_sim import (
    build_spec_and_players,
    derive_top_cut_player_ids,
    fetch_active_player_count_from_games,
)
from sim_engine import initialize_state
from sim_models import load_draw_model_artifact
from tournament_sim_runner import run_simulation_from_state


TOP_CUT_BUCKETS = [index / 10 for index in range(11)]
WINNER_BUCKETS = [0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]
CUT_LINE_BUCKETS = [0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]


@dataclass(frozen=True)
class ModelSpec:
    label: str
    path: str


def fetch_candidate_tournaments(
    client: SupabaseClient,
    *,
    limit: int,
    min_player_count: int,
    start_date_from: str | None,
    start_date_to: str | None,
) -> list[dict[str, Any]]:
    params = {
        "select": "id,name,start_date,player_count,top_cut",
        "top_cut": "gt.0",
        "player_count": f"gte.{min_player_count}",
        "order": "start_date.desc",
        "limit": str(limit),
    }
    if start_date_from:
        params["start_date"] = f"gte.{start_date_from}"
    if start_date_to:
        params["start_date"] = f"lt.{start_date_to}"
    return client.select("tournaments", params, max_retries=8)


def parse_model(value: str) -> ModelSpec:
    if "=" not in value:
        raise argparse.ArgumentTypeError("model must be LABEL=PATH")
    label, path = value.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("model must be LABEL=PATH")
    return ModelSpec(label=label, path=path)


def probability_at_point(distribution: list[dict[str, Any]], actual_points: int | None) -> float:
    if actual_points is None:
        return 0.0
    for row in distribution:
        try:
            if int(row["points"]) == actual_points:
                return float(row["probability"])
        except (KeyError, TypeError, ValueError):
            continue
    return 0.0


def expected_points(distribution: list[dict[str, Any]]) -> float | None:
    total = 0.0
    probability_total = 0.0
    for row in distribution:
        try:
            points = float(row["points"])
            probability = float(row["probability"])
        except (KeyError, TypeError, ValueError):
            continue
        total += points * probability
        probability_total += probability
    return total / probability_total if probability_total else None


def actual_points_at_rank(entries: list[dict[str, Any]], rank: int) -> int | None:
    for row in entries:
        try:
            if int(row.get("final_standing")) == rank:
                return int(row.get("points") or 0)
        except (TypeError, ValueError):
            continue
    return None


def top_cut_recall(probabilities: dict[str, float], actual_top_cut_ids: set[str], n: int) -> float | None:
    if not actual_top_cut_ids or n <= 0:
        return None
    predicted = {
        player_id
        for player_id, _ in sorted(probabilities.items(), key=lambda item: item[1], reverse=True)[:n]
    }
    return len(predicted & actual_top_cut_ids) / len(actual_top_cut_ids)


def brier_score(observations: list[tuple[float, int]]) -> float | None:
    if not observations:
        return None
    return fmean((probability - actual) ** 2 for probability, actual in observations)


def bucket_rows(observations: list[tuple[float, int]], buckets: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for left, right in zip(buckets, buckets[1:], strict=True):
        if right == buckets[-1]:
            values = [(p, y) for p, y in observations if left <= p <= right]
        else:
            values = [(p, y) for p, y in observations if left <= p < right]
        if not values:
            continue
        rows.append(
            {
                "bucket": [left, right],
                "count": len(values),
                "avg_predicted": fmean(p for p, _ in values),
                "actual_rate": fmean(y for _, y in values),
            }
        )
    return rows


def evaluate_model_on_tournament(
    client: SupabaseClient,
    model: Any,
    *,
    model_label: str,
    tournament_id: str,
    simulations: int,
    seed: int,
    workers: int | None,
    repeat_avoidance_max_pods: int,
) -> dict[str, Any]:
    spec, players, entries, feature_context = build_spec_and_players(
        client,
        tournament_id,
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        active_players_only=True,
    )
    state = initialize_state(spec, players, feature_context=feature_context)
    summary = run_simulation_from_state(
        state,
        model,
        simulations=simulations,
        seed=seed,
        workers=workers,
        collect_detailed_metrics=True,
    )

    player_ids = [player.player_id for player in players]
    actual_top_cut_ids = derive_top_cut_player_ids(entries, spec.top_cut)
    actual_winner_id = next((str(row["player_id"]) for row in entries if row.get("final_standing") == 1), None)
    actual_cut_line_points = actual_points_at_rank(entries, spec.top_cut)
    top_cut_probabilities = {player_id: float(summary["top_cut_probability"].get(player_id, 0.0)) for player_id in player_ids}
    winner_probabilities = {player_id: float(summary["win_probability"].get(player_id, 0.0)) for player_id in player_ids}
    cut_line_distribution = summary["point_requirements"]["top_cut"]
    expected_cut_line = expected_points(cut_line_distribution)
    cut_line_actual_probability = probability_at_point(cut_line_distribution, actual_cut_line_points)

    top_n_values = sorted({spec.top_cut, 8, 10, 16, 20, 32, 40, 64})
    top_n_recall = {
        str(n): recall
        for n in top_n_values
        if (recall := top_cut_recall(top_cut_probabilities, actual_top_cut_ids, n)) is not None
    }

    return {
        "model": model_label,
        "tournament": {
            "id": spec.tournament_id,
            "name": spec.name,
            "player_count": spec.player_count,
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "actual": {
            "winner_id": actual_winner_id,
            "top_cut_count": len(actual_top_cut_ids),
            "cut_line_points": actual_cut_line_points,
        },
        "metrics": {
            "winner_probability": winner_probabilities.get(actual_winner_id or "", 0.0),
            "winner_log_loss": -math.log(max(winner_probabilities.get(actual_winner_id or "", 0.0), 1e-9)),
            "cut_line_probability_at_actual": cut_line_actual_probability,
            "cut_line_log_loss": -math.log(max(cut_line_actual_probability, 1e-9)),
            "cut_line_expected_abs_error": (
                abs(expected_cut_line - actual_cut_line_points)
                if expected_cut_line is not None and actual_cut_line_points is not None
                else None
            ),
            "cut_line_mode_hit": int(
                actual_cut_line_points is not None
                and bool(cut_line_distribution)
                and max(cut_line_distribution, key=lambda row: float(row["probability"]))["points"] == actual_cut_line_points
            ),
            "top_cut_brier": brier_score(
                [(top_cut_probabilities[player_id], int(player_id in actual_top_cut_ids)) for player_id in player_ids]
            ),
            "winner_brier": brier_score(
                [(winner_probabilities[player_id], int(player_id == actual_winner_id)) for player_id in player_ids]
            ),
            "top_cut_recall_at_n": top_n_recall,
        },
        "calibration_inputs": {
            "top_cut": [(top_cut_probabilities[player_id], int(player_id in actual_top_cut_ids)) for player_id in player_ids],
            "winner": [(winner_probabilities[player_id], int(player_id == actual_winner_id)) for player_id in player_ids],
            "cut_line": [
                (float(row["probability"]), int(actual_cut_line_points is not None and int(row["points"]) == actual_cut_line_points))
                for row in cut_line_distribution
            ]
            + ([(0.0, 1)] if actual_cut_line_points is not None and cut_line_actual_probability == 0.0 else []),
        },
        "simulations": simulations,
    }


def average_metric(results: list[dict[str, Any]], path: tuple[str, ...]) -> float | None:
    values: list[float] = []
    for result in results:
        node: Any = result
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if node is not None:
            values.append(float(node))
    return fmean(values) if values else None


def aggregate_model_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"events": 0}

    top_cut_observations: list[tuple[float, int]] = []
    winner_observations: list[tuple[float, int]] = []
    cut_line_observations: list[tuple[float, int]] = []
    recall_values: dict[str, list[float]] = {}
    for result in results:
        top_cut_observations.extend(result["calibration_inputs"]["top_cut"])
        winner_observations.extend(result["calibration_inputs"]["winner"])
        cut_line_observations.extend(result["calibration_inputs"]["cut_line"])
        for n, recall in result["metrics"]["top_cut_recall_at_n"].items():
            recall_values.setdefault(n, []).append(float(recall))

    return {
        "events": len(results),
        "average_metrics": {
            "winner_probability": average_metric(results, ("metrics", "winner_probability")),
            "winner_log_loss": average_metric(results, ("metrics", "winner_log_loss")),
            "winner_brier": average_metric(results, ("metrics", "winner_brier")),
            "top_cut_brier": average_metric(results, ("metrics", "top_cut_brier")),
            "cut_line_probability_at_actual": average_metric(results, ("metrics", "cut_line_probability_at_actual")),
            "cut_line_log_loss": average_metric(results, ("metrics", "cut_line_log_loss")),
            "cut_line_expected_abs_error": average_metric(results, ("metrics", "cut_line_expected_abs_error")),
            "cut_line_mode_hit_rate": average_metric(results, ("metrics", "cut_line_mode_hit")),
            "top_cut_recall_at_n": {n: fmean(values) for n, values in sorted(recall_values.items(), key=lambda item: int(item[0]))},
        },
        "calibration": {
            "cut_line_probability_buckets": bucket_rows(cut_line_observations, CUT_LINE_BUCKETS),
            "top_cut_probability_buckets": bucket_rows(top_cut_observations, TOP_CUT_BUCKETS),
            "winner_probability_buckets": bucket_rows(winner_observations, WINNER_BUCKETS),
        },
    }


def strip_calibration_inputs(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "calibration_inputs"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", type=parse_model, required=True, help="LABEL=PATH")
    parser.add_argument("--simulations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--candidate-scan-limit", type=int, default=50)
    parser.add_argument("--min-active-player-count", type=int, default=100)
    parser.add_argument("--start-date-from")
    parser.add_argument("--start-date-to")
    parser.add_argument("--repeat-avoidance-max-pods", type=int, default=32)
    parser.add_argument("--include-event-details", action="store_true")
    args = parser.parse_args()

    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])

    candidate_rows = fetch_candidate_tournaments(
        client,
        limit=args.candidate_scan_limit,
        min_player_count=args.min_active_player_count,
        start_date_from=args.start_date_from,
        start_date_to=args.start_date_to,
    )
    tournaments: list[dict[str, Any]] = []
    for row in candidate_rows:
        active_count = fetch_active_player_count_from_games(client, str(row["id"]))
        if active_count >= args.min_active_player_count:
            tournaments.append({**row, "active_player_count": active_count})
        if len(tournaments) >= args.limit:
            break

    models = {spec.label: load_draw_model_artifact(spec.path) for spec in args.model}
    results_by_model: dict[str, list[dict[str, Any]]] = {spec.label: [] for spec in args.model}
    errors: list[dict[str, Any]] = []

    for tournament_index, tournament in enumerate(tournaments):
        tournament_id = str(tournament["id"])
        for model_index, spec in enumerate(args.model):
            case_seed = args.seed + (tournament_index * 10_000) + (model_index * 1_000_000)
            try:
                results_by_model[spec.label].append(
                    evaluate_model_on_tournament(
                        client,
                        models[spec.label],
                        model_label=spec.label,
                        tournament_id=tournament_id,
                        simulations=args.simulations,
                        seed=case_seed,
                        workers=args.workers,
                        repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
                    )
                )
            except Exception as exc:  # pragma: no cover - CLI reporting path
                errors.append({"model": spec.label, "tournament_id": tournament_id, "error": str(exc)})

    output = {
        "config": {
            "simulations": args.simulations,
            "workers": args.workers,
            "limit": args.limit,
            "candidate_scan_limit": args.candidate_scan_limit,
            "min_active_player_count": args.min_active_player_count,
            "repeat_avoidance_max_pods": args.repeat_avoidance_max_pods,
            "models": {spec.label: spec.path for spec in args.model},
        },
        "tournaments": tournaments,
        "aggregate": {
            label: aggregate_model_results(results)
            for label, results in results_by_model.items()
        },
        "errors": errors,
    }
    if args.include_event_details:
        output["results"] = {
            label: [strip_calibration_inputs(result) for result in results]
            for label, results in results_by_model.items()
        }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
