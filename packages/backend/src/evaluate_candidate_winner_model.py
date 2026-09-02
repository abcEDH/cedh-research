#!/usr/bin/env python3
"""Evaluate draw model plus candidate-player winner model.

This compares the current winner baseline, which uses round-updated Elo shares,
against a candidate-level model trained on one row per player in decisive pods.
The draw probability still comes from a draw-only model; this script only tests
whether a learned winner share can improve on Elo once a pod is decisive.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ingest import SupabaseClient, load_local_env
from rebuild_global_elo_tables import DEFAULT_RATING, SEAT_ELO_BONUS
from sim_models import CANDIDATE_WINNER_FEATURES
from train_draw_model import DEFAULT_CACHE_PATH

from evaluate_pod_outcome_vs_draw_elo import (
    EPSILON,
    apply_round_elo_updates,
    decisive_win_shares,
    fetch_participant_inputs,
    is_valid_outcome_row,
    load_cached_rows,
    old_baseline_probabilities,
    rating_before_start,
    round_group_key,
    round_sort_key,
    row_date,
    row_value,
    select_features,
    split_by_tournament,
    make_x as make_pod_x,
    fit_draw_model,
    predict_draw_probability,
    build_elo_history,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_REPORT_PATH = DATA_DIR / "candidate_winner_model_eval.json"
DEFAULT_PARTICIPANT_CACHE_PATH = DATA_DIR / "candidate_winner_eval_participants.pkl"


CANDIDATE_FEATURES = CANDIDATE_WINNER_FEATURES


@dataclass(frozen=True)
class CandidateExample:
    game_id: str
    tournament_id: str
    player_id: str
    label: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class GameCandidatePrediction:
    old_probability: float
    candidate_probability: float
    blend_probabilities: dict[str, float]
    is_draw: bool
    is_swiss: bool
    segment_keys: tuple[str, ...]


def maybe_limit_train_tournaments(train_rows: list[Any], limit: int | None) -> list[Any]:
    if not limit or limit <= 0:
        return train_rows
    first_date_by_tournament: dict[str, datetime] = {}
    for row in train_rows:
        tournament_id = str(row_value(row, "tournament_id", "") or "")
        if not tournament_id:
            continue
        date = row_date(row)
        current = first_date_by_tournament.get(tournament_id)
        if current is None or date < current:
            first_date_by_tournament[tournament_id] = date
    selected = set(
        sorted(first_date_by_tournament, key=lambda tournament_id: (first_date_by_tournament[tournament_id], tournament_id))[-limit:]
    )
    return [row for row in train_rows if str(row_value(row, "tournament_id", "") or "") in selected]


def group_result_rows(result_rows: list[dict[str, Any]]) -> tuple[
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, str],
    dict[str, set[str]],
]:
    games_by_tournament: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    tournament_start: dict[str, str] = {}
    players_by_tournament: dict[str, set[str]] = defaultdict(set)
    for row in result_rows:
        game_id = str(row.get("game_id") or "")
        tournament_id = str(row.get("tournament_id") or "")
        player_id = str(row.get("player_id") or "")
        if not game_id or not tournament_id or not player_id:
            continue
        games_by_tournament[tournament_id][game_id].append(row)
        players_by_tournament[tournament_id].add(player_id)
        start_date = str(row.get("start_date") or "")
        if start_date and (tournament_id not in tournament_start or start_date < tournament_start[tournament_id]):
            tournament_start[tournament_id] = start_date
    return games_by_tournament, tournament_start, players_by_tournament


def seat_by_player(game_rows: list[dict[str, Any]], seats_by_entry: dict[tuple[str, str], int]) -> dict[str, int]:
    seats: dict[str, int] = {}
    for row in game_rows:
        game_id = str(row.get("game_id") or "")
        entry_id = str(row.get("entry_id") or "")
        player_id = str(row.get("player_id") or "")
        if not game_id or not entry_id or not player_id:
            continue
        seat = seats_by_entry.get((game_id, entry_id))
        if seat is not None:
            seats[player_id] = seat
    return seats


def candidate_feature_tuple(
    cache_row: Any,
    game_rows: list[dict[str, Any]],
    player_id: str,
    ratings: dict[str, float],
    seats_by_entry: dict[tuple[str, str], int],
    elo_shares: dict[str, float],
) -> tuple[float, ...]:
    player_ids = [str(row.get("player_id") or "") for row in game_rows if row.get("player_id")]
    seats = seat_by_player(game_rows, seats_by_entry)
    raw_seat = seats.get(player_id)
    use_seat_bonus = len(player_ids) == 4 and sorted(seats.values()) == [0, 1, 2, 3]
    seat_bonus = SEAT_ELO_BONUS.get((raw_seat or 0) + 1, 0.0) if use_seat_bonus and raw_seat is not None else 0.0
    candidate_elo = float(ratings.get(player_id, DEFAULT_RATING))
    candidate_effective_elo = candidate_elo + seat_bonus
    effective_elos: dict[str, float] = {}
    for other_id in player_ids:
        other_raw_seat = seats.get(other_id)
        other_bonus = SEAT_ELO_BONUS.get((other_raw_seat or 0) + 1, 0.0) if use_seat_bonus and other_raw_seat is not None else 0.0
        effective_elos[other_id] = float(ratings.get(other_id, DEFAULT_RATING)) + other_bonus
    sorted_elos = sorted(effective_elos.values(), reverse=True)
    pod_size = len(player_ids)
    candidate_rank = 1 + sum(1 for value in effective_elos.values() if value > candidate_effective_elo)
    candidate_percentile = 1.0 if pod_size <= 1 else 1.0 - ((candidate_rank - 1) / (pod_size - 1))
    best_elo = sorted_elos[0] if sorted_elos else candidate_effective_elo
    second_elo = sorted_elos[1] if len(sorted_elos) > 1 else best_elo
    min_elo = sorted_elos[-1] if sorted_elos else candidate_effective_elo
    mean_elo = float(sum(sorted_elos) / len(sorted_elos)) if sorted_elos else candidate_effective_elo
    std_elo = float(np.std(np.asarray(sorted_elos, dtype=float))) if sorted_elos else 0.0
    values = {
        "pod_size": float(row_value(cache_row, "pod_size", pod_size) or pod_size),
        "is_swiss": float(row_value(cache_row, "is_swiss", 0) or 0),
        "round_number": float(row_value(cache_row, "round_number", 0) or 0),
        "swiss_progress": float(row_value(cache_row, "swiss_progress", 0.0) or 0.0),
        "is_last_swiss_round": float(row_value(cache_row, "is_last_swiss_round", 0) or 0),
        "is_penultimate_swiss_round": float(row_value(cache_row, "is_penultimate_swiss_round", 0) or 0),
        "tournament_size": float(row_value(cache_row, "tournament_size", 0) or 0),
        "cut_fraction": float(row_value(cache_row, "cut_fraction", 0.0) or 0.0),
        "size_bucket": float(row_value(cache_row, "size_bucket", 0) or 0),
        "candidate_seat": float((raw_seat + 1) if raw_seat is not None else 0),
        "candidate_has_seat": 1.0 if raw_seat is not None else 0.0,
        "candidate_seat_bonus": float(seat_bonus),
        "candidate_elo": float(candidate_elo),
        "candidate_effective_elo": float(candidate_effective_elo),
        "candidate_elo_share": float(elo_shares.get(player_id, 1.0 / max(1, pod_size))),
        "candidate_elo_rank": float(candidate_rank),
        "candidate_elo_percentile": float(candidate_percentile),
        "candidate_gap_to_best": float(candidate_effective_elo - best_elo),
        "candidate_gap_to_second": float(candidate_effective_elo - second_elo),
        "candidate_gap_to_mean": float(candidate_effective_elo - mean_elo),
        "candidate_gap_to_min": float(candidate_effective_elo - min_elo),
        "candidate_is_best_elo": 1.0 if candidate_rank == 1 else 0.0,
        "candidate_is_second_elo": 1.0 if candidate_rank == 2 else 0.0,
        "candidate_is_worst_elo": 1.0 if candidate_rank == pod_size else 0.0,
        "pod_elo_spread": float(best_elo - min_elo),
        "pod_elo_mean": float(mean_elo),
        "pod_elo_std": float(std_elo),
    }
    return tuple(values[name] for name in CANDIDATE_FEATURES)


def build_candidate_examples(rows: list[Any], participant_inputs: dict[str, Any]) -> list[CandidateExample]:
    row_by_game_id = {str(row_value(row, "game_id", "") or ""): row for row in rows}
    result_rows = participant_inputs["result_rows"]
    seats_by_entry = {
        (str(row.get("game_id")), str(row.get("entry_id"))): int(row.get("seat_position"))
        for row in participant_inputs["seat_rows"]
        if row.get("game_id") and row.get("entry_id") and row.get("seat_position") is not None
    }
    elo_history = build_elo_history(participant_inputs["elo_event_rows"])
    games_by_tournament, tournament_start, players_by_tournament = group_result_rows(result_rows)
    examples: list[CandidateExample] = []

    for tournament_id in sorted(games_by_tournament, key=lambda value: tournament_start.get(value, "")):
        ratings = {
            player_id: rating_before_start(player_id, tournament_start.get(tournament_id, ""), elo_history)
            for player_id in players_by_tournament[tournament_id]
        }
        round_groups: dict[tuple[int, int, str], list[list[dict[str, Any]]]] = defaultdict(list)
        for game_rows in games_by_tournament[tournament_id].values():
            if str(game_rows[0].get("game_id") or "") in row_by_game_id:
                round_groups[round_group_key(game_rows)].append(game_rows)
        for _round_key, round_games in sorted(round_groups.items(), key=lambda item: item[0]):
            for game_rows in sorted(round_games, key=round_sort_key):
                game_id = str(game_rows[0].get("game_id") or "")
                cache_row = row_by_game_id.get(game_id)
                if cache_row is None:
                    continue
                has_draw = any(str(row.get("result") or "").lower() == "draw" for row in game_rows)
                winner_id = next((str(row.get("player_id")) for row in game_rows if str(row.get("result") or "").lower() == "win"), None)
                if has_draw or not winner_id:
                    continue
                elo_shares = decisive_win_shares(game_rows, ratings, seats_by_entry)
                for result_row in game_rows:
                    player_id = str(result_row.get("player_id") or "")
                    if not player_id:
                        continue
                    examples.append(
                        CandidateExample(
                            game_id=game_id,
                            tournament_id=tournament_id,
                            player_id=player_id,
                            label=1 if player_id == winner_id else 0,
                            features=candidate_feature_tuple(
                                cache_row,
                                game_rows,
                                player_id,
                                ratings,
                                seats_by_entry,
                                elo_shares,
                            ),
                        )
                    )
            apply_round_elo_updates(round_games, ratings, seats_by_entry)
    return examples


def make_candidate_x(examples: list[CandidateExample]) -> np.ndarray:
    return np.asarray([example.features for example in examples], dtype=np.float32)


def fit_candidate_model(examples: list[CandidateExample]) -> HistGradientBoostingClassifier:
    x_matrix = make_candidate_x(examples)
    y_vector = np.asarray([example.label for example in examples], dtype=int)
    model = HistGradientBoostingClassifier(
        loss="log_loss",
        random_state=0,
        learning_rate=0.06,
        max_leaf_nodes=31,
        min_samples_leaf=300,
        max_depth=None,
        l2_regularization=0.0,
    )
    model.fit(x_matrix, y_vector)
    return model


def candidate_scores_by_game(model: HistGradientBoostingClassifier, examples: list[CandidateExample]) -> dict[str, dict[str, float]]:
    if not examples:
        return {}
    x_matrix = make_candidate_x(examples)
    probabilities = model.predict_proba(x_matrix)
    classes = [int(value) for value in model.classes_]
    positive_index = classes.index(1) if 1 in classes else -1
    raw_by_game: dict[str, dict[str, float]] = defaultdict(dict)
    for example, row_probabilities in zip(examples, probabilities, strict=True):
        score = float(row_probabilities[positive_index]) if positive_index >= 0 else 0.0
        raw_by_game[example.game_id][example.player_id] = max(0.0, score)
    normalized: dict[str, dict[str, float]] = {}
    for game_id, player_scores in raw_by_game.items():
        total = sum(player_scores.values())
        if total <= 0:
            size = max(1, len(player_scores))
            normalized[game_id] = {player_id: 1.0 / size for player_id in player_scores}
        else:
            normalized[game_id] = {player_id: score / total for player_id, score in player_scores.items()}
    return normalized


def actual_winner_by_game(examples: list[CandidateExample]) -> dict[str, str]:
    winners: dict[str, str] = {}
    for example in examples:
        if example.label == 1:
            winners[example.game_id] = example.player_id
    return winners


def elo_share_by_game(examples: list[CandidateExample]) -> dict[str, dict[str, float]]:
    share_index = CANDIDATE_FEATURES.index("candidate_elo_share")
    shares: dict[str, dict[str, float]] = defaultdict(dict)
    for example in examples:
        shares[example.game_id][example.player_id] = float(example.features[share_index])
    return shares


def row_segment_keys(row: Any) -> tuple[str, ...]:
    keys = ["all"]
    is_swiss = int(row_value(row, "is_swiss", 0)) == 1
    is_draw = int(row_value(row, "is_draw", 0)) == 1
    keys.append("swiss" if is_swiss else "top_cut")
    keys.append("draws" if is_draw else "decisive")
    if is_swiss and is_draw:
        keys.append("swiss_draws")
    if is_swiss and not is_draw:
        keys.append("swiss_decisive")
    if not is_swiss:
        keys.append("top_cut_decisive")
    keys.append(f"pod_size_{int(row_value(row, 'pod_size', 0) or 0)}")
    return tuple(keys)


def evaluate_rows(
    rows: list[Any],
    old_probability_by_game: dict[str, float],
    draw_probabilities: list[float],
    candidate_share_by_game: dict[str, dict[str, float]],
    elo_share_by_game_id: dict[str, dict[str, float]],
    winner_by_game: dict[str, str],
    blend_weights: list[float],
) -> list[GameCandidatePrediction]:
    draw_probability_by_game = {
        str(row_value(row, "game_id", "") or ""): float(probability)
        for row, probability in zip(rows, draw_probabilities, strict=True)
    }
    output: list[GameCandidatePrediction] = []
    for row in rows:
        game_id = str(row_value(row, "game_id", "") or "")
        if game_id not in old_probability_by_game:
            continue
        is_draw = int(row_value(row, "is_draw", 0)) == 1
        is_swiss = int(row_value(row, "is_swiss", 0)) == 1
        if is_draw:
            draw_probability = draw_probability_by_game.get(game_id, 0.0) if is_swiss else 0.0
            blend_probabilities = {f"{weight:.2f}": draw_probability for weight in blend_weights}
            output.append(
                GameCandidatePrediction(
                    old_probability=old_probability_by_game[game_id],
                    candidate_probability=draw_probability,
                    blend_probabilities=blend_probabilities,
                    is_draw=True,
                    is_swiss=is_swiss,
                    segment_keys=row_segment_keys(row),
                )
            )
            continue
        winner_id = winner_by_game.get(game_id)
        if not winner_id:
            continue
        decisive_probability = 1.0 - draw_probability_by_game.get(game_id, 0.0) if is_swiss else 1.0
        candidate_share = candidate_share_by_game.get(game_id, {}).get(winner_id, 0.0)
        elo_share = elo_share_by_game_id.get(game_id, {}).get(winner_id, 0.0)
        blend_probabilities = {
            f"{weight:.2f}": decisive_probability * ((weight * candidate_share) + ((1.0 - weight) * elo_share))
            for weight in blend_weights
        }
        output.append(
            GameCandidatePrediction(
                old_probability=old_probability_by_game[game_id],
                candidate_probability=decisive_probability * candidate_share,
                blend_probabilities=blend_probabilities,
                is_draw=False,
                is_swiss=is_swiss,
                segment_keys=row_segment_keys(row),
            )
        )
    return output


def log_loss(values: list[float]) -> float:
    return float(np.mean([-math.log(max(EPSILON, min(1.0, value))) for value in values])) if values else 0.0


def select_blend_weight(validation_predictions: list[GameCandidatePrediction], blend_weights: list[float]) -> float:
    losses = {
        weight: log_loss([prediction.blend_probabilities[f"{weight:.2f}"] for prediction in validation_predictions])
        for weight in blend_weights
    }
    return min(losses, key=lambda weight: (losses[weight], weight))


def summarize(predictions: list[GameCandidatePrediction], selected_weight: float) -> dict[str, Any]:
    by_segment: dict[str, list[GameCandidatePrediction]] = defaultdict(list)
    for prediction in predictions:
        for key in prediction.segment_keys:
            by_segment[key].append(prediction)
    preferred_order = [
        "all",
        "swiss",
        "top_cut",
        "decisive",
        "draws",
        "swiss_decisive",
        "swiss_draws",
        "top_cut_decisive",
        "pod_size_2",
        "pod_size_3",
        "pod_size_4",
    ]
    ordered_keys = [key for key in preferred_order if key in by_segment] + sorted(
        key for key in by_segment if key not in preferred_order
    )
    selected_key = f"{selected_weight:.2f}"
    output: dict[str, Any] = {}
    for key in ordered_keys:
        rows = by_segment[key]
        old_loss = log_loss([row.old_probability for row in rows])
        candidate_loss = log_loss([row.candidate_probability for row in rows])
        selected_blend_loss = log_loss([row.blend_probabilities[selected_key] for row in rows])
        output[key] = {
            "rows": len(rows),
            "old_draw_plus_elo_log_loss": old_loss,
            "candidate_only_log_loss": candidate_loss,
            "selected_blend_log_loss": selected_blend_loss,
            "candidate_delta_new_minus_old": candidate_loss - old_loss,
            "selected_blend_delta_new_minus_old": selected_blend_loss - old_loss,
        }
    return output


def parse_blend_weights(value: str) -> list[float]:
    weights = sorted({float(part.strip()) for part in value.split(",") if part.strip()})
    if not weights:
        raise argparse.ArgumentTypeError("blend weights cannot be empty")
    if weights[0] < 0.0 or weights[-1] > 1.0:
        raise argparse.ArgumentTypeError("blend weights must be between 0 and 1")
    return weights


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--participant-cache-path", default=str(DEFAULT_PARTICIPANT_CACHE_PATH))
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--limit-train-tournaments", type=int)
    parser.add_argument("--limit-test-tournaments", type=int)
    parser.add_argument("--blend-weights", type=parse_blend_weights, default=parse_blend_weights("0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1"))
    args = parser.parse_args()

    started = time.perf_counter()
    load_local_env()
    rows = [row for row in load_cached_rows(Path(args.cache_path)) if is_valid_outcome_row(row) and row_value(row, "tournament_id")]
    train_rows, test_rows, split_metadata = split_by_tournament(rows, args.test_fraction)
    train_rows = maybe_limit_train_tournaments(train_rows, args.limit_train_tournaments)
    test_rows = maybe_limit_train_tournaments(test_rows, args.limit_test_tournaments)
    candidate_train_rows, validation_rows, validation_metadata = split_by_tournament(train_rows, args.validation_fraction)
    all_needed_rows = candidate_train_rows + validation_rows + train_rows + test_rows
    print(
        f"Rows: train_inner={len(candidate_train_rows):,}, validation={len(validation_rows):,}, "
        f"train_full={len(train_rows):,}, test={len(test_rows):,}",
        flush=True,
    )

    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    participant_inputs = fetch_participant_inputs(
        client,
        all_needed_rows,
        participant_cache_path=Path(args.participant_cache_path) if args.participant_cache_path else None,
    )

    pod_features = select_features(include_topdeck_elo_features=False)

    print("Training validation draw and candidate models...", flush=True)
    validation_draw_model = fit_draw_model(candidate_train_rows, pod_features)
    validation_candidate_examples = build_candidate_examples(candidate_train_rows, participant_inputs)
    validation_candidate_model = fit_candidate_model(validation_candidate_examples)
    validation_x = make_pod_x(validation_rows, pod_features)
    validation_draw_probabilities = predict_draw_probability(validation_draw_model, validation_x).tolist()
    validation_old_probability_by_game = old_baseline_probabilities(validation_rows, validation_draw_probabilities, participant_inputs)
    validation_eval_examples = build_candidate_examples(validation_rows, participant_inputs)
    validation_candidate_shares = candidate_scores_by_game(validation_candidate_model, validation_eval_examples)
    validation_elo_shares = elo_share_by_game(validation_eval_examples)
    validation_winners = actual_winner_by_game(validation_eval_examples)
    validation_predictions = evaluate_rows(
        validation_rows,
        validation_old_probability_by_game,
        validation_draw_probabilities,
        validation_candidate_shares,
        validation_elo_shares,
        validation_winners,
        args.blend_weights,
    )
    selected_weight = select_blend_weight(validation_predictions, args.blend_weights)
    print(f"Selected blend weight on validation: {selected_weight:.2f}", flush=True)

    print("Training final draw and candidate models...", flush=True)
    final_draw_model = fit_draw_model(train_rows, pod_features)
    final_candidate_examples = build_candidate_examples(train_rows, participant_inputs)
    final_candidate_model = fit_candidate_model(final_candidate_examples)
    test_x = make_pod_x(test_rows, pod_features)
    test_draw_probabilities = predict_draw_probability(final_draw_model, test_x).tolist()
    test_old_probability_by_game = old_baseline_probabilities(test_rows, test_draw_probabilities, participant_inputs)
    test_eval_examples = build_candidate_examples(test_rows, participant_inputs)
    test_candidate_shares = candidate_scores_by_game(final_candidate_model, test_eval_examples)
    test_elo_shares = elo_share_by_game(test_eval_examples)
    test_winners = actual_winner_by_game(test_eval_examples)
    test_predictions = evaluate_rows(
        test_rows,
        test_old_probability_by_game,
        test_draw_probabilities,
        test_candidate_shares,
        test_elo_shares,
        test_winners,
        args.blend_weights,
    )

    validation_blend_losses = {
        f"{weight:.2f}": log_loss([prediction.blend_probabilities[f"{weight:.2f}"] for prediction in validation_predictions])
        for weight in args.blend_weights
    }
    test_blend_losses = {
        f"{weight:.2f}": log_loss([prediction.blend_probabilities[f"{weight:.2f}"] for prediction in test_predictions])
        for weight in args.blend_weights
    }
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "runtime_seconds": time.perf_counter() - started,
        "split": split_metadata,
        "validation_split": validation_metadata,
        "rows": {
            "loaded_valid": len(rows),
            "train_inner": len(candidate_train_rows),
            "validation": len(validation_rows),
            "train_full": len(train_rows),
            "test": len(test_rows),
            "candidate_train_inner_examples": len(validation_candidate_examples),
            "candidate_train_full_examples": len(final_candidate_examples),
            "test_candidate_examples": len(test_eval_examples),
            "test_evaluated": len(test_predictions),
        },
        "candidate_features": CANDIDATE_FEATURES,
        "selected_blend_weight": selected_weight,
        "validation_blend_log_loss": validation_blend_losses,
        "test_blend_log_loss": test_blend_losses,
        "metrics": summarize(test_predictions, selected_weight),
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2), flush=True)
    print(f"Wrote report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
