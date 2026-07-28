#!/usr/bin/env python3
"""Compare pod-outcome prediction against draw-model plus round-updated Elo.

The rich pod cache contains model features and outcome labels, but not the
participant ids needed to reconstruct Elo winner shares. This evaluator uses
the cache for train/test features, then fetches held-out game participants and
historical Elo events from Supabase to score the old baseline without using
same-round or future event results.
"""

from __future__ import annotations

import argparse
import bisect
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
from sim_models import load_draw_model_artifact
from rebuild_global_elo_tables import (
    DEFAULT_RATING,
    ELO_BASE,
    ELO_DIVISOR,
    K_FACTOR_DECISIVE,
    K_FACTOR_DRAW,
    SEAT_ELO_BONUS,
    bracket_round_sort_value,
    parse_datetime_utc,
)
from train_draw_model import DEFAULT_CACHE_PATH, parse_datetime_value, score_probs
from train_pod_outcome_model import feature_value, select_outcome_features


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DEFAULT_REPORT_PATH = DATA_DIR / "pod_outcome_vs_draw_elo_eval.json"
DEFAULT_PARTICIPANT_CACHE_PATH = DATA_DIR / "pod_outcome_eval_participants.pkl"
DEFAULT_DRAW_ARTIFACT_PATHS = [
    MODELS_DIR / "pod-outcome" / "v4" / "pod_outcome_model_artifact_v4_draw_elo_hybrid.pkl",
]
EPSILON = 1e-9


@dataclass(frozen=True)
class EvaluatedRow:
    row: Any
    old_probability: float
    new_probability: float
    segment_keys: tuple[str, ...]


@dataclass(frozen=True)
class OutcomePredictionDetails:
    actual_probability: float
    draw_probability: float
    conditional_winner_probability: float | None


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def row_value(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def row_date(row: Any) -> datetime:
    value = row_value(row, "date")
    if isinstance(value, datetime):
        return value
    return parse_datetime_value(value)


def load_cached_rows(cache_path: Path) -> list[Any]:
    started = time.perf_counter()
    with cache_path.open("rb") as handle:
        rows = pickle.load(handle)
    print(f"Loaded cache rows: {len(rows):,} in {time.perf_counter() - started:.1f}s", flush=True)
    return rows


def is_valid_outcome_row(row: Any) -> bool:
    try:
        pod_size = int(row_value(row, "pod_size", 0))
        is_draw = int(row_value(row, "is_draw", 0))
        winner_index = int(row_value(row, "winner_index", -1))
    except (TypeError, ValueError):
        return False
    return 2 <= pod_size <= 4 and (is_draw == 1 or 0 <= winner_index < pod_size)


def outcome_label(row: Any) -> int:
    if int(row_value(row, "is_draw", 0)) == 1:
        return 0
    return int(row_value(row, "winner_index", -1)) + 1


def select_features(feature_set: str, *, include_topdeck_elo_features: bool) -> list[str]:
    return select_outcome_features(feature_set, include_topdeck_elo_features=include_topdeck_elo_features)


def make_x(rows: list[Any], features: list[str]) -> np.ndarray:
    return np.asarray(
        [[feature_value(row, feature) for feature in features] for row in rows],
        dtype=float,
    )


def split_by_tournament(rows: list[Any], test_fraction: float) -> tuple[list[Any], list[Any], dict[str, Any]]:
    first_date_by_tournament: dict[str, datetime] = {}
    for row in rows:
        tournament_id = str(row_value(row, "tournament_id", "") or "")
        if not tournament_id:
            continue
        date = row_date(row)
        current = first_date_by_tournament.get(tournament_id)
        if current is None or date < current:
            first_date_by_tournament[tournament_id] = date
    tournaments = sorted(first_date_by_tournament, key=lambda tournament_id: (first_date_by_tournament[tournament_id], tournament_id))
    if len(tournaments) < 2:
        raise RuntimeError("Need at least two tournaments with ids to create a chronological split")
    test_count = max(1, int(round(len(tournaments) * test_fraction)))
    test_tournaments = set(tournaments[-test_count:])
    train_tournaments = set(tournaments[:-test_count])
    train_rows = [row for row in rows if str(row_value(row, "tournament_id", "") or "") in train_tournaments]
    test_rows = [row for row in rows if str(row_value(row, "tournament_id", "") or "") in test_tournaments]
    metadata = {
        "tournaments": {
            "train": len(train_tournaments),
            "test": len(test_tournaments),
            "total": len(tournaments),
        },
        "date_range": {
            "train_start": first_date_by_tournament[tournaments[0]].isoformat(),
            "train_end": first_date_by_tournament[tournaments[-test_count - 1]].isoformat() if len(tournaments) > test_count else None,
            "test_start": first_date_by_tournament[tournaments[-test_count]].isoformat(),
            "test_end": first_date_by_tournament[tournaments[-1]].isoformat(),
        },
    }
    return train_rows, test_rows, metadata


def maybe_limit_test_tournaments(test_rows: list[Any], limit: int | None) -> list[Any]:
    if not limit or limit <= 0:
        return test_rows
    first_date_by_tournament: dict[str, datetime] = {}
    for row in test_rows:
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
    return [row for row in test_rows if str(row_value(row, "tournament_id", "") or "") in selected]


def maybe_limit_train_rows(train_rows: list[Any], limit: int | None) -> list[Any]:
    if not limit or limit <= 0 or len(train_rows) <= limit:
        return train_rows
    # Keep the newest rows in the training window.
    return sorted(train_rows, key=lambda row: (row_date(row), str(row_value(row, "game_id", ""))))[-limit:]


def fit_draw_model(rows: list[Any], features: list[str]) -> HistGradientBoostingClassifier:
    x_matrix = make_x(rows, features)
    y_vector = np.asarray([int(row_value(row, "is_draw", 0)) for row in rows], dtype=int)
    model = HistGradientBoostingClassifier(
        loss="log_loss",
        random_state=0,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=250,
        max_depth=None,
        l2_regularization=0.0,
    )
    model.fit(x_matrix, y_vector)
    return model


def fit_outcome_model(rows: list[Any], features: list[str]) -> HistGradientBoostingClassifier:
    x_matrix = make_x(rows, features)
    y_vector = np.asarray([outcome_label(row) for row in rows], dtype=int)
    model = HistGradientBoostingClassifier(
        loss="log_loss",
        random_state=0,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=250,
        max_depth=None,
        l2_regularization=0.0,
    )
    model.fit(x_matrix, y_vector)
    return model


def predict_draw_probability(model: HistGradientBoostingClassifier, x_matrix: np.ndarray) -> np.ndarray:
    probabilities = model.predict_proba(x_matrix)
    classes = [int(value) for value in model.classes_]
    if 1 not in classes:
        return np.zeros(x_matrix.shape[0], dtype=float)
    return probabilities[:, classes.index(1)].astype(float)


def predict_draw_artifact_probability(artifact_path: Path, rows: list[Any]) -> tuple[np.ndarray, dict[str, Any]]:
    loaded = load_draw_model_artifact(artifact_path)
    x_matrix = make_x(rows, loaded.features)
    probabilities = loaded.model.predict_proba(x_matrix)
    classes = [int(value) for value in getattr(loaded.model, "classes_", loaded.classes)]
    positive_class = loaded.draw_class
    if positive_class not in classes:
        draw_probabilities = np.zeros(x_matrix.shape[0], dtype=float)
    else:
        draw_probabilities = probabilities[:, classes.index(positive_class)].astype(float)
    if loaded.calibrator is not None and loaded.target != "pod_outcome":
        if loaded.calibration == "platt":
            draw_probabilities = loaded.calibrator.predict_proba(draw_probabilities.reshape(-1, 1))[:, 1]
        else:
            draw_probabilities = loaded.calibrator.predict(draw_probabilities)
    return np.clip(draw_probabilities, 0.0, 1.0), {
        "path": str(artifact_path),
        "target": loaded.target,
        "draw_class": loaded.draw_class,
        "winner_source": loaded.winner_source,
        "feature_count": len(loaded.features),
        "calibration": loaded.calibration,
    }


def predict_outcome_probability_details(
    model: HistGradientBoostingClassifier,
    rows: list[Any],
    x_matrix: np.ndarray,
) -> list[OutcomePredictionDetails]:
    probabilities = model.predict_proba(x_matrix)
    classes = [int(value) for value in model.classes_]
    predicted: list[OutcomePredictionDetails] = []
    for row, row_probabilities in zip(rows, probabilities, strict=True):
        class_probability = {
            class_label: float(probability)
            for class_label, probability in zip(classes, row_probabilities, strict=False)
        }
        pod_size = int(row_value(row, "pod_size", 0))
        is_swiss = int(row_value(row, "is_swiss", 0)) == 1
        is_draw = int(row_value(row, "is_draw", 0)) == 1
        raw_draw_probability = max(0.0, min(1.0, class_probability.get(0, 0.0)))
        draw_probability = raw_draw_probability if is_swiss else 0.0
        valid_win_total = sum(max(0.0, class_probability.get(index, 0.0)) for index in range(1, pod_size + 1))
        if is_draw:
            predicted.append(
                OutcomePredictionDetails(
                    actual_probability=draw_probability,
                    draw_probability=draw_probability,
                    conditional_winner_probability=None,
                )
            )
            continue
        winner_class = int(row_value(row, "winner_index", -1)) + 1
        if valid_win_total <= 0:
            conditional_win_probability = 1.0 / max(1, pod_size)
        else:
            conditional_win_probability = max(0.0, class_probability.get(winner_class, 0.0)) / valid_win_total
        decisive_probability = 1.0 - draw_probability if is_swiss else 1.0
        predicted.append(
            OutcomePredictionDetails(
                actual_probability=max(0.0, min(1.0, decisive_probability * conditional_win_probability)),
                draw_probability=draw_probability,
                conditional_winner_probability=max(0.0, min(1.0, conditional_win_probability)),
            )
        )
    return predicted


def predict_outcome_probabilities(
    model: HistGradientBoostingClassifier,
    rows: list[Any],
    x_matrix: np.ndarray,
) -> list[float]:
    return [
        details.actual_probability
        for details in predict_outcome_probability_details(model, rows, x_matrix)
    ]


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    *,
    label: str,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.select(table, {**params, "limit": str(limit), "offset": str(offset)}, max_retries=8)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        if offset % 25_000 == 0:
            print(f"Fetched {offset:,} rows from {label}", flush=True)
    return rows


def in_filter(values: list[str]) -> str:
    return "(" + ",".join(values) + ")"


def load_participant_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return pickle.load(handle)


def save_participant_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(payload, handle)


def fetch_participant_inputs(
    client: SupabaseClient,
    test_rows: list[Any],
    *,
    participant_cache_path: Path | None,
) -> dict[str, Any]:
    game_ids = sorted({str(row_value(row, "game_id", "") or "") for row in test_rows if row_value(row, "game_id", "")})
    cache_key = {
        "game_ids": game_ids,
        "version": 1,
    }
    cached = load_participant_cache(participant_cache_path) if participant_cache_path else None
    if cached and cached.get("cache_key") == cache_key:
        print(f"Loaded participant cache: {participant_cache_path}", flush=True)
        return cached["payload"]

    print(f"Fetching participant rows for {len(game_ids):,} held-out games...", flush=True)
    result_rows: list[dict[str, Any]] = []
    seat_rows: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunked(game_ids, 200), start=1):
        result_rows.extend(
            fetch_all(
                client,
                "global_elo_game_results",
                {
                    "select": "game_id,tournament_id,start_date,entry_id,player_id,result,is_draw,round_number,round_name,table_number",
                    "game_id": f"in.{in_filter(chunk)}",
                    "result": "neq.bye",
                },
                label="heldout_global_elo_game_results",
            )
        )
        seat_rows.extend(
            fetch_all(
                client,
                "game_participants",
                {
                    "select": "game_id,entry_id,seat_position",
                    "game_id": f"in.{in_filter(chunk)}",
                },
                label="heldout_game_participants",
            )
        )
        if index % 25 == 0:
            print(f"Fetched participant chunks: {index:,}/{math.ceil(len(game_ids) / 200):,}", flush=True)

    tournament_start: dict[str, str] = {}
    player_ids_by_tournament: dict[str, set[str]] = defaultdict(set)
    for row in result_rows:
        tournament_id = str(row.get("tournament_id") or "")
        player_id = str(row.get("player_id") or "")
        start_date = str(row.get("start_date") or "")
        if tournament_id and player_id:
            player_ids_by_tournament[tournament_id].add(player_id)
        if tournament_id and start_date and (tournament_id not in tournament_start or start_date < tournament_start[tournament_id]):
            tournament_start[tournament_id] = start_date
    all_player_ids = sorted({player_id for player_ids in player_ids_by_tournament.values() for player_id in player_ids})
    latest_start = max(tournament_start.values()) if tournament_start else datetime.utcnow().isoformat()

    print(f"Fetching historical Elo events for {len(all_player_ids):,} held-out players...", flush=True)
    elo_event_rows: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunked(all_player_ids, 40), start=1):
        elo_event_rows.extend(
            fetch_all(
                client,
                "global_elo_game_events",
                {
                    "select": "player_id,game_date,rating_after",
                    "region_type": "eq.global",
                    "region_key": "eq.ALL",
                    "game_date": f"lt.{latest_start}",
                    "player_id": f"in.{in_filter(chunk)}",
                    "order": "game_date.asc",
                },
                label="heldout_global_elo_game_events",
            )
        )
        if index % 50 == 0:
            print(f"Fetched Elo event chunks: {index:,}/{math.ceil(len(all_player_ids) / 40):,}", flush=True)

    payload = {
        "result_rows": result_rows,
        "seat_rows": seat_rows,
        "elo_event_rows": elo_event_rows,
    }
    if participant_cache_path:
        save_participant_cache(participant_cache_path, {"cache_key": cache_key, "payload": payload})
        print(f"Saved participant cache: {participant_cache_path}", flush=True)
    return payload


def round_sort_key(rows: list[dict[str, Any]]) -> tuple[int, int, str, int, str]:
    first = rows[0]
    round_number = first.get("round_number")
    try:
        swiss_round = int(round_number) if round_number is not None else None
    except (TypeError, ValueError):
        swiss_round = None
    round_name = str(first.get("round_name") or "")
    table_number_raw = first.get("table_number")
    try:
        table_number = int(table_number_raw) if table_number_raw is not None else 999_999
    except (TypeError, ValueError):
        table_number = 999_999
    if swiss_round is not None:
        return (0, swiss_round, "", table_number, str(first.get("game_id") or ""))
    return (1, bracket_round_sort_value(round_name), round_name, table_number, str(first.get("game_id") or ""))


def round_group_key(rows: list[dict[str, Any]]) -> tuple[int, int, str]:
    sort_key = round_sort_key(rows)
    return sort_key[:3]


def seat_by_player_for_game(game_rows: list[dict[str, Any]], seats_by_entry: dict[tuple[str, str], int]) -> dict[str, int]:
    seats: dict[str, int] = {}
    for row in game_rows:
        player_id = str(row.get("player_id") or "")
        entry_id = str(row.get("entry_id") or "")
        game_id = str(row.get("game_id") or "")
        if not player_id or not entry_id:
            continue
        seat = seats_by_entry.get((game_id, entry_id))
        if seat is not None:
            seats[player_id] = seat
    return seats


def rating_equity(rating: float) -> float:
    return math.pow(ELO_BASE, rating / ELO_DIVISOR)


def decisive_win_shares(game_rows: list[dict[str, Any]], ratings: dict[str, float], seats_by_entry: dict[tuple[str, str], int]) -> dict[str, float]:
    player_ids = [str(row.get("player_id") or "") for row in game_rows if row.get("player_id")]
    seats_by_player = seat_by_player_for_game(game_rows, seats_by_entry)
    use_seat_bonus = len(player_ids) == 4 and sorted(seats_by_player.values()) == [0, 1, 2, 3]
    equities: dict[str, float] = {}
    for player_id in player_ids:
        effective_rating = float(ratings.get(player_id, DEFAULT_RATING))
        if use_seat_bonus:
            effective_rating += SEAT_ELO_BONUS.get(seats_by_player[player_id] + 1, 0.0)
        equities[player_id] = rating_equity(effective_rating)
    total = sum(equities.values()) or 1.0
    return {player_id: equity / total for player_id, equity in equities.items()}


def apply_round_elo_updates(
    round_games: list[list[dict[str, Any]]],
    ratings: dict[str, float],
    seats_by_entry: dict[tuple[str, str], int],
) -> None:
    deltas: dict[str, float] = defaultdict(float)
    for game_rows in round_games:
        player_ids = [str(row.get("player_id") or "") for row in game_rows if row.get("player_id")]
        if len(player_ids) < 2:
            continue
        has_draw = any(str(row.get("result") or "").lower() == "draw" for row in game_rows)
        draw_count = sum(1 for row in game_rows if str(row.get("result") or "").lower() == "draw")
        winner_id = next((str(row.get("player_id")) for row in game_rows if str(row.get("result") or "").lower() == "win"), None)
        shares = decisive_win_shares(game_rows, ratings, seats_by_entry)
        k_factor = K_FACTOR_DRAW if has_draw else K_FACTOR_DECISIVE
        for player_id in player_ids:
            if has_draw and draw_count:
                actual = 1.0 / draw_count if any(str(row.get("player_id")) == player_id and str(row.get("result") or "").lower() == "draw" for row in game_rows) else 0.0
            else:
                actual = 1.0 if player_id == winner_id else 0.0
            deltas[player_id] += k_factor * (actual - shares.get(player_id, 0.0))
    for player_id, delta in deltas.items():
        ratings[player_id] = round(float(ratings.get(player_id, DEFAULT_RATING)) + delta, 6)


def build_elo_history(elo_event_rows: list[dict[str, Any]]) -> dict[str, tuple[list[datetime], list[float]]]:
    grouped: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    for row in elo_event_rows:
        player_id = str(row.get("player_id") or "")
        game_date = parse_datetime_utc(str(row.get("game_date") or ""))
        rating_after = row.get("rating_after")
        if not player_id or game_date is None or rating_after is None:
            continue
        grouped[player_id].append((game_date, float(rating_after)))
    history: dict[str, tuple[list[datetime], list[float]]] = {}
    for player_id, values in grouped.items():
        values.sort(key=lambda item: item[0])
        history[player_id] = ([item[0] for item in values], [item[1] for item in values])
    return history


def rating_before_start(player_id: str, start_date: str, elo_history: dict[str, tuple[list[datetime], list[float]]]) -> float:
    parsed_start = parse_datetime_utc(start_date)
    if parsed_start is None:
        return DEFAULT_RATING
    dates, ratings = elo_history.get(player_id, ([], []))
    index = bisect.bisect_left(dates, parsed_start) - 1
    return ratings[index] if index >= 0 else DEFAULT_RATING


def old_baseline_probability_details(
    test_rows: list[Any],
    draw_probabilities: list[float],
    participant_inputs: dict[str, Any],
) -> tuple[dict[str, float], dict[str, float]]:
    draw_probability_by_game = {
        str(row_value(row, "game_id", "") or ""): float(probability)
        for row, probability in zip(test_rows, draw_probabilities, strict=True)
    }
    result_rows = participant_inputs["result_rows"]
    seats_by_entry = {
        (str(row.get("game_id")), str(row.get("entry_id"))): int(row.get("seat_position"))
        for row in participant_inputs["seat_rows"]
        if row.get("game_id") and row.get("entry_id") and row.get("seat_position") is not None
    }
    elo_history = build_elo_history(participant_inputs["elo_event_rows"])
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

    probabilities: dict[str, float] = {}
    conditional_winner_probabilities: dict[str, float] = {}
    for tournament_id in sorted(games_by_tournament, key=lambda value: tournament_start.get(value, "")):
        ratings = {
            player_id: rating_before_start(player_id, tournament_start.get(tournament_id, ""), elo_history)
            for player_id in players_by_tournament[tournament_id]
        }
        round_groups: dict[tuple[int, int, str], list[list[dict[str, Any]]]] = defaultdict(list)
        for game_rows in games_by_tournament[tournament_id].values():
            round_groups[round_group_key(game_rows)].append(game_rows)
        for _round_key, round_games in sorted(round_groups.items(), key=lambda item: item[0]):
            for game_rows in sorted(round_games, key=round_sort_key):
                game_id = str(game_rows[0].get("game_id") or "")
                is_swiss = game_rows[0].get("round_number") is not None
                has_draw = any(str(row.get("result") or "").lower() == "draw" for row in game_rows)
                winner_id = next((str(row.get("player_id")) for row in game_rows if str(row.get("result") or "").lower() == "win"), None)
                if has_draw:
                    probabilities[game_id] = max(0.0, min(1.0, draw_probability_by_game.get(game_id, 0.0))) if is_swiss else 0.0
                elif winner_id:
                    shares = decisive_win_shares(game_rows, ratings, seats_by_entry)
                    decisive_probability = 1.0 - max(0.0, min(1.0, draw_probability_by_game.get(game_id, 0.0))) if is_swiss else 1.0
                    conditional_winner_probability = shares.get(winner_id, 0.0)
                    conditional_winner_probabilities[game_id] = conditional_winner_probability
                    probabilities[game_id] = decisive_probability * conditional_winner_probability
            apply_round_elo_updates(round_games, ratings, seats_by_entry)
    return probabilities, conditional_winner_probabilities


def old_baseline_probabilities(
    test_rows: list[Any],
    draw_probabilities: list[float],
    participant_inputs: dict[str, Any],
) -> dict[str, float]:
    return old_baseline_probability_details(test_rows, draw_probabilities, participant_inputs)[0]


def segment_keys(row: Any) -> tuple[str, ...]:
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
    keys.append(f"pod_size_{int(row_value(row, 'pod_size', 0))}")
    if is_swiss:
        round_number = int(row_value(row, "round_number", 0) or 0)
        if round_number == 1:
            keys.append("round_1")
        elif int(row_value(row, "is_last_swiss_round", 0) or 0) == 1:
            keys.append("last_swiss_round")
        elif int(row_value(row, "is_penultimate_swiss_round", 0) or 0) == 1:
            keys.append("penultimate_swiss_round")
    else:
        round_name = str(row_value(row, "round_name", "") or "").strip().lower()
        if round_name:
            keys.append("top_cut_" + round_name.replace(" ", "_"))
    return tuple(keys)


def summarize(evaluated_rows: list[EvaluatedRow]) -> dict[str, Any]:
    by_segment: dict[str, list[EvaluatedRow]] = defaultdict(list)
    for row in evaluated_rows:
        for key in row.segment_keys:
            by_segment[key].append(row)
    preferred_order = [
        "all",
        "swiss",
        "top_cut",
        "decisive",
        "draws",
        "swiss_decisive",
        "swiss_draws",
        "top_cut_decisive",
        "round_1",
        "penultimate_swiss_round",
        "last_swiss_round",
        "top_cut_top_16",
        "top_cut_top_8",
        "top_cut_semifinals",
        "top_cut_finals",
        "pod_size_2",
        "pod_size_3",
        "pod_size_4",
    ]
    ordered_keys = [key for key in preferred_order if key in by_segment] + sorted(
        key for key in by_segment if key not in preferred_order
    )
    output: dict[str, Any] = {}
    for key in ordered_keys:
        rows = by_segment[key]
        old_losses = [-math.log(max(EPSILON, min(1.0, row.old_probability))) for row in rows]
        new_losses = [-math.log(max(EPSILON, min(1.0, row.new_probability))) for row in rows]
        old_log_loss = float(np.mean(old_losses))
        new_log_loss = float(np.mean(new_losses))
        output[key] = {
            "rows": len(rows),
            "old_draw_plus_round_updated_elo_log_loss": old_log_loss,
            "new_pod_outcome_log_loss": new_log_loss,
            "delta_new_minus_old": new_log_loss - old_log_loss,
            "old_avg_actual_probability": float(np.mean([max(0.0, min(1.0, row.old_probability)) for row in rows])),
            "new_avg_actual_probability": float(np.mean([max(0.0, min(1.0, row.new_probability)) for row in rows])),
        }
    return output


def preferred_segment_order(by_segment: dict[str, Any]) -> list[str]:
    preferred_order = [
        "all",
        "swiss",
        "top_cut",
        "decisive",
        "draws",
        "swiss_decisive",
        "swiss_draws",
        "top_cut_decisive",
        "round_1",
        "penultimate_swiss_round",
        "last_swiss_round",
        "top_cut_top_16",
        "top_cut_top_8",
        "top_cut_semifinals",
        "top_cut_finals",
        "pod_size_2",
        "pod_size_3",
        "pod_size_4",
    ]
    return [key for key in preferred_order if key in by_segment] + sorted(
        key for key in by_segment if key not in preferred_order
    )


def tournament_draw_rate_error(rows: list[Any], probabilities: list[float]) -> dict[str, Any]:
    grouped: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for row, probability in zip(rows, probabilities, strict=True):
        tournament_id = str(row_value(row, "tournament_id", "") or "")
        if tournament_id:
            grouped[tournament_id].append((row, float(probability)))
    if not grouped:
        return {"tournaments": 0, "mae": 0.0, "weighted_mae": 0.0}
    errors = []
    weighted_errors = []
    weights = []
    for grouped_rows in grouped.values():
        actual_rate = float(np.mean([int(row_value(row, "is_draw", 0)) for row, _probability in grouped_rows]))
        predicted_rate = float(np.mean([probability for _row, probability in grouped_rows]))
        error = abs(predicted_rate - actual_rate)
        errors.append(error)
        weighted_errors.append(error * len(grouped_rows))
        weights.append(len(grouped_rows))
    return {
        "tournaments": len(grouped),
        "mae": float(np.mean(errors)),
        "weighted_mae": float(sum(weighted_errors) / max(1, sum(weights))),
    }


def summarize_draw_probabilities(rows: list[Any], probabilities: list[float]) -> dict[str, Any]:
    by_segment: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for row, probability in zip(rows, probabilities, strict=True):
        clipped_probability = max(0.0, min(1.0, float(probability)))
        for key in segment_keys(row):
            by_segment[key].append((row, clipped_probability))

    output: dict[str, Any] = {}
    for key in preferred_segment_order(by_segment):
        pairs = by_segment[key]
        labels = np.asarray([int(row_value(row, "is_draw", 0)) for row, _probability in pairs], dtype=int)
        predicted = np.asarray([probability for _row, probability in pairs], dtype=float)
        log_loss, brier = score_probs(labels, predicted)
        segment_rows = [row for row, _probability in pairs]
        output[key] = {
            "rows": len(pairs),
            "actual_draw_rate": float(np.mean(labels)) if len(labels) else 0.0,
            "predicted_draw_rate": float(np.mean(predicted)) if len(predicted) else 0.0,
            "predicted_minus_actual_draw_rate": float(np.mean(predicted) - np.mean(labels)) if len(labels) else 0.0,
            "draw_log_loss": log_loss,
            "draw_brier": brier,
            "tournament_draw_rate_error": tournament_draw_rate_error(segment_rows, predicted.tolist()),
        }
    return output


def summarize_actual_probabilities(rows: list[Any], probability_by_game: dict[str, float]) -> dict[str, Any]:
    by_segment: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for row in rows:
        game_id = str(row_value(row, "game_id", "") or "")
        probability = probability_by_game.get(game_id)
        if probability is None:
            continue
        clipped_probability = max(0.0, min(1.0, float(probability)))
        for key in segment_keys(row):
            by_segment[key].append((row, clipped_probability))

    output: dict[str, Any] = {}
    for key in preferred_segment_order(by_segment):
        pairs = by_segment[key]
        losses = [-math.log(max(EPSILON, probability)) for _row, probability in pairs]
        output[key] = {
            "rows": len(pairs),
            "actual_outcome_log_loss": float(np.mean(losses)),
            "avg_actual_probability": float(np.mean([probability for _row, probability in pairs])),
        }
    return output


def summarize_conditional_winner_probabilities(
    rows: list[Any],
    old_probability_by_game: dict[str, float],
    new_probability_by_game: dict[str, float],
) -> dict[str, Any]:
    by_segment: dict[str, list[EvaluatedRow]] = defaultdict(list)
    for row in rows:
        if int(row_value(row, "is_draw", 0)) == 1:
            continue
        game_id = str(row_value(row, "game_id", "") or "")
        old_probability = old_probability_by_game.get(game_id)
        new_probability = new_probability_by_game.get(game_id)
        if old_probability is None or new_probability is None:
            continue
        evaluated = EvaluatedRow(
            row=row,
            old_probability=max(0.0, min(1.0, float(old_probability))),
            new_probability=max(0.0, min(1.0, float(new_probability))),
            segment_keys=segment_keys(row),
        )
        for key in evaluated.segment_keys:
            by_segment[key].append(evaluated)

    output: dict[str, Any] = {}
    for key in preferred_segment_order(by_segment):
        rows_for_segment = by_segment[key]
        old_losses = [-math.log(max(EPSILON, min(1.0, row.old_probability))) for row in rows_for_segment]
        new_losses = [-math.log(max(EPSILON, min(1.0, row.new_probability))) for row in rows_for_segment]
        old_log_loss = float(np.mean(old_losses))
        new_log_loss = float(np.mean(new_losses))
        output[key] = {
            "rows": len(rows_for_segment),
            "round_updated_elo_conditional_winner_log_loss": old_log_loss,
            "new_pod_outcome_conditional_winner_log_loss": new_log_loss,
            "delta_new_minus_elo": new_log_loss - old_log_loss,
            "elo_avg_actual_winner_probability": float(np.mean([row.old_probability for row in rows_for_segment])),
            "new_avg_actual_winner_probability": float(np.mean([row.new_probability for row in rows_for_segment])),
        }
    return output


def artifact_label(path: Path) -> str:
    parent = path.parent.name
    return parent if parent.startswith("v") else path.stem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--participant-cache-path", default=str(DEFAULT_PARTICIPANT_CACHE_PATH))
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--max-train-rows", type=int, help="Use only the newest N train rows for quicker experiments.")
    parser.add_argument("--limit-test-tournaments", type=int, help="Use only the newest N held-out tournaments.")
    parser.add_argument("--feature-set", choices=("default", "v3"), default="v3")
    parser.add_argument("--include-topdeck-elo-features", action="store_true")
    parser.add_argument(
        "--draw-artifact",
        action="append",
        dest="draw_artifacts",
        help="Persisted draw/pod-outcome artifact to compare. Defaults to the recommended v4 hybrid.",
    )
    parser.add_argument("--skip-draw-artifact-comparison", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    load_local_env()
    cache_path = Path(args.cache_path)
    report_path = Path(args.report_path)
    participant_cache_path = Path(args.participant_cache_path) if args.participant_cache_path else None

    rows = [row for row in load_cached_rows(cache_path) if is_valid_outcome_row(row) and row_value(row, "tournament_id")]
    print(f"Valid outcome rows with tournament ids: {len(rows):,}", flush=True)
    train_rows, test_rows, split_metadata = split_by_tournament(rows, args.test_fraction)
    test_rows = maybe_limit_test_tournaments(test_rows, args.limit_test_tournaments)
    train_rows = maybe_limit_train_rows(train_rows, args.max_train_rows)
    print(f"Train rows: {len(train_rows):,}; test rows: {len(test_rows):,}", flush=True)

    features = select_features(args.feature_set, include_topdeck_elo_features=args.include_topdeck_elo_features)
    print(f"Training with {len(features):,} features", flush=True)
    draw_model = fit_draw_model(train_rows, features)
    outcome_model = fit_outcome_model(train_rows, features)

    x_test = make_x(test_rows, features)
    draw_probabilities = predict_draw_probability(draw_model, x_test).tolist()
    new_details = predict_outcome_probability_details(outcome_model, test_rows, x_test)
    new_probabilities = [details.actual_probability for details in new_details]
    new_draw_probabilities = [details.draw_probability for details in new_details]
    new_conditional_winner_probability_by_game = {
        str(row_value(row, "game_id", "") or ""): float(details.conditional_winner_probability)
        for row, details in zip(test_rows, new_details, strict=True)
        if details.conditional_winner_probability is not None
    }

    client = SupabaseClient(
        url=os.environ["SUPABASE_URL"],
        service_key=os.environ["SUPABASE_SERVICE_KEY"],
    )
    participant_inputs = fetch_participant_inputs(
        client,
        test_rows,
        participant_cache_path=participant_cache_path,
    )
    old_probability_by_game, old_conditional_winner_probability_by_game = old_baseline_probability_details(
        test_rows,
        draw_probabilities,
        participant_inputs,
    )
    evaluated_rows: list[EvaluatedRow] = []
    missing_old_probability = 0
    for row, new_probability in zip(test_rows, new_probabilities, strict=True):
        game_id = str(row_value(row, "game_id", "") or "")
        old_probability = old_probability_by_game.get(game_id)
        if old_probability is None:
            missing_old_probability += 1
            continue
        evaluated_rows.append(
            EvaluatedRow(
                row=row,
                old_probability=old_probability,
                new_probability=new_probability,
                segment_keys=segment_keys(row),
            )
        )
    draw_artifact_reports: dict[str, Any] = {}
    if not args.skip_draw_artifact_comparison:
        draw_artifact_paths = (
            [Path(path) for path in args.draw_artifacts]
            if args.draw_artifacts
            else list(DEFAULT_DRAW_ARTIFACT_PATHS)
        )
        for artifact_path in draw_artifact_paths:
            label = artifact_label(artifact_path)
            if not artifact_path.exists():
                draw_artifact_reports[label] = {"path": str(artifact_path), "missing": True}
                continue
            artifact_draw_probabilities, artifact_metadata = predict_draw_artifact_probability(artifact_path, test_rows)
            artifact_outcome_probability_by_game, _artifact_conditional_by_game = old_baseline_probability_details(
                test_rows,
                artifact_draw_probabilities.tolist(),
                participant_inputs,
            )
            draw_artifact_reports[label] = {
                "artifact": artifact_metadata,
                "draw_metrics": summarize_draw_probabilities(test_rows, artifact_draw_probabilities.tolist()),
                "draw_plus_round_updated_elo_outcome_metrics": summarize_actual_probabilities(
                    test_rows,
                    artifact_outcome_probability_by_game,
                ),
            }

    metrics = {
        "full_outcome": {
            "fresh_draw_model_plus_round_updated_elo_vs_new_pod_outcome": summarize(evaluated_rows),
            "draw_artifact_plus_round_updated_elo": {
                label: value.get("draw_plus_round_updated_elo_outcome_metrics", {})
                for label, value in draw_artifact_reports.items()
                if not value.get("missing")
            },
        },
        "draw": {
            "fresh_train_split_draw_model": summarize_draw_probabilities(test_rows, draw_probabilities),
            "new_pod_outcome": summarize_draw_probabilities(test_rows, new_draw_probabilities),
            "artifacts": {
                label: value.get("draw_metrics", {})
                for label, value in draw_artifact_reports.items()
                if not value.get("missing")
            },
        },
        "conditional_winner": {
            "round_updated_elo_vs_new_pod_outcome": summarize_conditional_winner_probabilities(
                test_rows,
                old_conditional_winner_probability_by_game,
                new_conditional_winner_probability_by_game,
            )
        },
    }
    summary = {
        "new_pod_outcome_draw_swiss": metrics["draw"]["new_pod_outcome"].get("swiss", {}),
        "fresh_draw_model_swiss": metrics["draw"]["fresh_train_split_draw_model"].get("swiss", {}),
        "conditional_winner_all": metrics["conditional_winner"]["round_updated_elo_vs_new_pod_outcome"].get("all", {}),
        "full_outcome_all": metrics["full_outcome"]["fresh_draw_model_plus_round_updated_elo_vs_new_pod_outcome"].get("all", {}),
        "artifact_draw_swiss": {
            label: value.get("draw_metrics", {}).get("swiss", {})
            for label, value in draw_artifact_reports.items()
            if not value.get("missing")
        },
    }
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "runtime_seconds": time.perf_counter() - started,
        "cache_path": str(cache_path),
        "split": split_metadata,
        "features": {
            "count": len(features),
            "feature_set": args.feature_set,
            "include_topdeck_elo_features": bool(args.include_topdeck_elo_features),
        },
        "draw_artifacts": draw_artifact_reports,
        "rows": {
            "loaded_valid": len(rows),
            "train": len(train_rows),
            "test": len(test_rows),
            "evaluated": len(evaluated_rows),
            "missing_old_probability": missing_old_probability,
        },
        "summary": summary,
        "metrics": metrics,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Wrote report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
