#!/usr/bin/env python3
"""Backtest full historical tournament simulations across draw models."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
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
from sim_types import FeatureContext, SimPlayer, TournamentSpec
from tournament_sim_runner import run_simulation_from_state


TOP_CUT_BUCKETS = [index / 10 for index in range(11)]
WINNER_BUCKETS = [0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]
CUT_LINE_BUCKETS = [0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]


@dataclass(frozen=True)
class ModelSpec:
    label: str
    path: str


@dataclass(frozen=True)
class PreparedTournament:
    spec: TournamentSpec
    players: list[SimPlayer]
    entries: list[dict[str, Any]]
    feature_context: FeatureContext
    runtime_seconds: float


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


def log_progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def prepare_tournament(
    client: SupabaseClient,
    tournament_id: str,
    *,
    repeat_avoidance_max_pods: int,
) -> PreparedTournament:
    started = time.perf_counter()
    spec, players, entries, feature_context = build_spec_and_players(
        client,
        tournament_id,
        repeat_avoidance_max_pods=repeat_avoidance_max_pods,
        active_players_only=True,
    )
    return PreparedTournament(
        spec=spec,
        players=players,
        entries=entries,
        feature_context=feature_context,
        runtime_seconds=time.perf_counter() - started,
    )


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


def valid_swiss_cut_line_points(points: int | None, swiss_rounds: int) -> int | None:
    if points is None or points <= 0:
        return None
    max_possible_points = max(1, swiss_rounds) * 5
    if points > max_possible_points:
        return None
    return points


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
    for left, right in zip(buckets, buckets[1:]):
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


def evaluate_model_on_prepared_tournament(
    prepared: PreparedTournament,
    model: Any,
    *,
    model_label: str,
    simulations: int,
    seed: int,
    workers: int | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    spec = prepared.spec
    players = prepared.players
    entries = prepared.entries
    state = initialize_state(spec, players, feature_context=prepared.feature_context)
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
    actual_cut_line_points = valid_swiss_cut_line_points(
        actual_points_at_rank(entries, spec.top_cut),
        spec.swiss_rounds,
    )
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
            "cut_line_probability_at_actual": (
                cut_line_actual_probability if actual_cut_line_points is not None else None
            ),
            "cut_line_log_loss": (
                -math.log(max(cut_line_actual_probability, 1e-9))
                if actual_cut_line_points is not None
                else None
            ),
            "cut_line_expected_abs_error": (
                abs(expected_cut_line - actual_cut_line_points)
                if expected_cut_line is not None and actual_cut_line_points is not None
                else None
            ),
            "cut_line_mode_hit": (
                int(
                    bool(cut_line_distribution)
                    and max(cut_line_distribution, key=lambda row: float(row["probability"]))["points"] == actual_cut_line_points
                )
                if actual_cut_line_points is not None
                else None
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
            "cut_line": (
                [
                    (float(row["probability"]), int(int(row["points"]) == actual_cut_line_points))
                    for row in cut_line_distribution
                ]
                + ([(0.0, 1)] if cut_line_actual_probability == 0.0 else [])
                if actual_cut_line_points is not None
                else []
            ),
        },
        "simulations": simulations,
        "prepare_runtime_seconds": prepared.runtime_seconds,
        "runtime_seconds": time.perf_counter() - started,
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
        "runtime_seconds": {
            "total": sum(float(result.get("runtime_seconds") or 0.0) for result in results),
            "average": fmean(float(result.get("runtime_seconds") or 0.0) for result in results),
        },
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


def completed_success_cases(results_by_model: dict[str, list[dict[str, Any]]]) -> set[tuple[str, str]]:
    return {
        (label, str(result["tournament"]["id"]))
        for label, results in results_by_model.items()
        for result in results
        if isinstance(result.get("tournament"), dict) and result["tournament"].get("id")
    }


def completed_error_cases(errors: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(error.get("model")), str(error.get("tournament_id")))
        for error in errors
        if error.get("model") and error.get("tournament_id")
    }


def load_checkpoint(path: Path, model_labels: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_results = payload.get("results") or {}
    results_by_model = {
        label: list(raw_results.get(label) or [])
        for label in model_labels
    }
    for label, results in results_by_model.items():
        if results and "calibration_inputs" not in results[0]:
            raise RuntimeError(
                f"Cannot resume from {path}: results for {label} do not include calibration_inputs."
            )
    return results_by_model, list(payload.get("errors") or [])


def build_output_payload(
    *,
    started: float,
    status: str,
    args: argparse.Namespace,
    model_specs: list[ModelSpec],
    tournaments: list[dict[str, Any]],
    results_by_model: dict[str, list[dict[str, Any]]],
    errors: list[dict[str, Any]],
    candidate_selection_seconds: float,
    model_load_seconds: float,
) -> dict[str, Any]:
    total_cases = len(tournaments) * len(model_specs)
    completed_cases = len(completed_success_cases(results_by_model) | completed_error_cases(errors))
    return {
        "status": status,
        "config": {
            "simulations": args.simulations,
            "workers": args.workers,
            "limit": args.limit,
            "candidate_scan_limit": args.candidate_scan_limit,
            "min_active_player_count": args.min_active_player_count,
            "start_date_from": args.start_date_from,
            "start_date_to": args.start_date_to,
            "repeat_avoidance_max_pods": args.repeat_avoidance_max_pods,
            "models": {spec.label: spec.path for spec in model_specs},
        },
        "progress": {
            "completed_cases": completed_cases,
            "total_cases": total_cases,
            "successful_cases": sum(len(results) for results in results_by_model.values()),
            "error_cases": len(errors),
        },
        "runtime_seconds": {
            "total": time.perf_counter() - started,
            "candidate_selection": candidate_selection_seconds,
            "model_load": model_load_seconds,
        },
        "tournaments": tournaments,
        "aggregate": {
            label: aggregate_model_results(results)
            for label, results in results_by_model.items()
        },
        "errors": errors,
        "results": results_by_model,
    }


def output_for_stdout(payload: dict[str, Any], *, include_event_details: bool) -> dict[str, Any]:
    if include_event_details:
        return {
            **payload,
            "results": {
                label: [strip_calibration_inputs(result) for result in results]
                for label, results in payload.get("results", {}).items()
            },
        }
    return {key: value for key, value in payload.items() if key != "results"}


def main() -> None:
    started = time.perf_counter()
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
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write checkpoint/final JSON to this path after every event/model case.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume completed event/model cases from --output. Requires a checkpoint with calibration inputs.",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="When resuming, discard checkpointed error cases so they are retried.",
    )
    args = parser.parse_args()

    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    model_specs = list(args.model)
    model_labels = [spec.label for spec in model_specs]

    log_progress("Selecting candidate tournaments...")
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
    candidate_selection_seconds = time.perf_counter() - started
    log_progress(
        f"Selected {len(tournaments)} tournaments with active_player_count >= "
        f"{args.min_active_player_count} from {len(candidate_rows)} candidates."
    )

    model_load_started = time.perf_counter()
    models = {spec.label: load_draw_model_artifact(spec.path) for spec in model_specs}
    model_load_seconds = time.perf_counter() - model_load_started
    log_progress(f"Loaded {len(models)} models in {model_load_seconds:.1f}s.")

    if args.resume and not args.output:
        raise RuntimeError("--resume requires --output")
    if args.resume and args.output and args.output.exists() and args.output.stat().st_size > 0:
        results_by_model, errors = load_checkpoint(args.output, model_labels)
        if args.retry_errors and errors:
            log_progress(f"Retrying {len(errors)} checkpointed error cases from {args.output}.")
            errors = []
        log_progress(
            f"Resumed {len(completed_success_cases(results_by_model))} successful cases "
            f"and {len(errors)} errors from {args.output}."
        )
    else:
        results_by_model = {spec.label: [] for spec in model_specs}
        errors: list[dict[str, Any]] = []
    completed_cases = completed_success_cases(results_by_model) | completed_error_cases(errors)

    if args.output:
        write_json_atomic(
            args.output,
            build_output_payload(
                started=started,
                status="running",
                args=args,
                model_specs=model_specs,
                tournaments=tournaments,
                results_by_model=results_by_model,
                errors=errors,
                candidate_selection_seconds=candidate_selection_seconds,
                model_load_seconds=model_load_seconds,
            ),
        )

    total_cases = len(tournaments) * len(model_specs)
    prepared_by_tournament_id: dict[str, PreparedTournament] = {}
    for tournament_index, tournament in enumerate(tournaments):
        tournament_id = str(tournament["id"])
        pending_specs = [
            spec
            for spec in model_specs
            if (spec.label, tournament_id) not in completed_cases
        ]
        if not pending_specs:
            log_progress(
                f"[{tournament_index + 1}/{len(tournaments)}] "
                f"Skipping {tournament['name']} ({tournament_id}); all model cases already complete."
            )
            continue
        try:
            prepared = prepared_by_tournament_id.get(tournament_id)
            if prepared is None:
                prepare_started = time.perf_counter()
                prepared = prepare_tournament(
                    client,
                    tournament_id,
                    repeat_avoidance_max_pods=args.repeat_avoidance_max_pods,
                )
                prepared_by_tournament_id[tournament_id] = prepared
                log_progress(
                    f"[{tournament_index + 1}/{len(tournaments)}] Prepared "
                    f"{prepared.spec.name} ({prepared.spec.player_count} players, "
                    f"Top {prepared.spec.top_cut}) in {time.perf_counter() - prepare_started:.1f}s."
                )
        except Exception as exc:  # pragma: no cover - CLI reporting path
            for spec in pending_specs:
                errors.append({"model": spec.label, "tournament_id": tournament_id, "error": str(exc)})
            completed_cases = completed_success_cases(results_by_model) | completed_error_cases(errors)
            log_progress(f"ERROR preparing {tournament_id}: {exc}")
            if args.output:
                write_json_atomic(
                    args.output,
                    build_output_payload(
                        started=started,
                        status="running",
                        args=args,
                        model_specs=model_specs,
                        tournaments=tournaments,
                        results_by_model=results_by_model,
                        errors=errors,
                        candidate_selection_seconds=candidate_selection_seconds,
                        model_load_seconds=model_load_seconds,
                    ),
                )
            continue

        for spec in pending_specs:
            case_seed = args.seed + (tournament_index * 10_000)
            case_number = len(completed_cases) + 1
            log_progress(
                f"[case {case_number}/{total_cases}] Running {spec.label} on "
                f"{prepared.spec.name} with seed {case_seed}..."
            )
            try:
                results_by_model[spec.label].append(
                    evaluate_model_on_prepared_tournament(
                        prepared,
                        models[spec.label],
                        model_label=spec.label,
                        simulations=args.simulations,
                        seed=case_seed,
                        workers=args.workers,
                    )
                )
                runtime = results_by_model[spec.label][-1]["runtime_seconds"]
                log_progress(f"[case {case_number}/{total_cases}] Completed {spec.label} in {runtime:.1f}s.")
            except Exception as exc:  # pragma: no cover - CLI reporting path
                errors.append({"model": spec.label, "tournament_id": tournament_id, "error": str(exc)})
                log_progress(f"[case {case_number}/{total_cases}] ERROR {spec.label} {tournament_id}: {exc}")
            completed_cases = completed_success_cases(results_by_model) | completed_error_cases(errors)
            if args.output:
                write_json_atomic(
                    args.output,
                    build_output_payload(
                        started=started,
                        status="running",
                        args=args,
                        model_specs=model_specs,
                        tournaments=tournaments,
                        results_by_model=results_by_model,
                        errors=errors,
                        candidate_selection_seconds=candidate_selection_seconds,
                        model_load_seconds=model_load_seconds,
                    ),
                )

    output = build_output_payload(
        started=started,
        status="complete",
        args=args,
        model_specs=model_specs,
        tournaments=tournaments,
        results_by_model=results_by_model,
        errors=errors,
        candidate_selection_seconds=candidate_selection_seconds,
        model_load_seconds=model_load_seconds,
    )
    if args.output:
        write_json_atomic(args.output, output)
    print(json.dumps(output_for_stdout(output, include_event_details=args.include_event_details), indent=2))


if __name__ == "__main__":
    main()
