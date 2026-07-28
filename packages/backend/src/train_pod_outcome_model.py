#!/usr/bin/env python3
"""Train a pod-level full outcome model.

The target is class 0 for draw and class 1..N for the winning player position
inside the pod's ordered player list. Simulation consumes this artifact as
P(draw) plus per-player win probabilities instead of combining P(draw) with
Elo-derived decisive winner odds.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
from dataclasses import MISSING, asdict, dataclass, fields
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from ingest import SupabaseClient, load_local_env
from sim_models import outcome_v3_family_flags
from sim_types import (
    ALL_DRAW_FEATURES,
    COMMANDER_DRAW_FEATURES,
    LIVE_DEFAULTED_DRAW_FEATURES,
    OUTCOME_V3_DRAW_FEATURES,
    TOPDECK_ELO_DRAW_FEATURES,
)
from train_draw_model import (
    DEFAULT_CACHE_PATH,
    DrawPodRow,
    RESULTS_SELECT,
    SEATS_SELECT,
    TOPDECK_ELOS_SELECT,
    TOURNAMENTS_SELECT,
    build_rich_pod_cache,
    fetch_all,
    load_pods,
    parse_datetime_value,
    recency_weight,
    save_pods,
    score_probs,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_ARTIFACT_PATH = DATA_DIR / "pod_outcome_model_artifact.pkl"
DEFAULT_REPORT_PATH = DATA_DIR / "pod_outcome_model_report.json"


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


@dataclass(frozen=True)
class OutcomeModelSelection:
    feature_set_name: str
    features: list[str]
    half_life: int
    learning_rate: float
    max_leaf_nodes: int
    min_samples_leaf: int
    max_depth: int | None
    l2_regularization: float


def row_value(row: Any, key: str, default: Any = 0.0) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def row_float(row: Any, key: str, default: float = 0.0) -> float:
    value = row_value(row, key, default)
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def feature_value(row: Any, feature: str) -> float:
    if feature not in OUTCOME_V3_DRAW_FEATURES:
        return row_float(row, feature)

    flags = outcome_v3_family_flags(
        str(row_value(row, "series_key", "") or ""),
        str(row_value(row, "tournament_name", "") or ""),
    )
    if feature in flags:
        return flags[feature]

    high1600 = row_float(row, "high1600")
    high1700 = row_float(row, "high1700")
    high1800 = row_float(row, "high1800")
    cut_fraction = row_float(row, "cut_fraction")
    series_prior = row_float(row, "series_prior_draw_rate")
    global_recent = row_float(row, "global_recent_draw_rate_90d")
    round_number = row_float(row, "round_number")
    pod_size = row_float(row, "pod_size")
    high_stakes_like = flags["is_high_stakes_like_family"]
    series_minus_global = series_prior - global_recent

    values = {
        "elite_count_1600_x_cut_fraction": high1600 * cut_fraction,
        "elite_count_1700_x_cut_fraction": high1700 * cut_fraction,
        "elite_count_1800_x_cut_fraction": high1800 * cut_fraction,
        "elite_count_1700_x_series_prior": high1700 * series_prior,
        "elite_count_1800_x_series_prior": high1800 * series_prior,
        "all_players_1700_plus": 1.0 if pod_size > 0 and high1700 >= pod_size else 0.0,
        "all_players_1800_plus": 1.0 if pod_size > 0 and high1800 >= pod_size else 0.0,
        "top2_mean_elo_x_series_prior": row_float(row, "top2_mean_elo") * series_prior,
        "top3_mean_elo_x_series_prior": row_float(row, "top3_mean_elo") * series_prior,
        "top3_mean_elo_x_round_number": row_float(row, "top3_mean_elo") * round_number,
        "mean_elo_x_global_recent_draw_rate_90d": row_float(row, "mean_elo") * global_recent,
        "series_minus_global_prior": series_minus_global,
        "series_minus_global_prior_abs": abs(series_minus_global),
        "topdeck_invitational_x_series_prior": flags["is_topdeck_invitational_family"] * series_prior,
        "midseason_showdown_x_series_prior": flags["is_midseason_showdown_family"] * series_prior,
        "invitational_like_x_series_prior": flags["is_invitational_like_family"] * series_prior,
        "high_stakes_like_x_series_prior": high_stakes_like * series_prior,
        "invitational_like_x_high1700": flags["is_invitational_like_family"] * high1700,
        "high_stakes_like_x_high1700": high_stakes_like * high1700,
        "high_stakes_like_x_cut_fraction": high_stakes_like * cut_fraction,
        "high_stakes_like_x_round_number": high_stakes_like * round_number,
        "cut_or_bye_pressure_count": row_float(row, "count_must_win_for_cut")
        + row_float(row, "count_must_win_for_bye"),
        "draw_locks_cut_or_bye": 1.0
        if row_float(row, "all_players_draw_lock_cut") or row_float(row, "all_players_draw_lock_bye")
        else 0.0,
        "draw_hurts_cut_or_bye_status": 1.0
        if row_float(row, "draw_hurts_any_player_cut_status") or row_float(row, "draw_hurts_any_player_bye_status")
        else 0.0,
        "asymmetric_cut_or_bye_incentive": 1.0
        if row_float(row, "pod_has_asymmetric_cut_incentive") or row_float(row, "pod_has_asymmetric_bye_incentive")
        else 0.0,
        "draw_as_good_as_win_cut_or_bye_count": row_float(row, "draw_vs_win_status_same_count")
        + row_float(row, "count_players_draw_as_good_as_win_for_bye"),
        "must_win_cut_or_bye_count": row_float(row, "count_players_win_only_live")
        + row_float(row, "count_players_win_only_live_for_bye"),
    }
    return float(values.get(feature, 0.0))


def select_outcome_features(feature_set: str, *, include_topdeck_elo_features: bool = False) -> list[str]:
    if feature_set not in {"default", "v3"}:
        raise ValueError(f"Unknown pod outcome feature set: {feature_set}")
    excluded_features = COMMANDER_DRAW_FEATURES | LIVE_DEFAULTED_DRAW_FEATURES | set(OUTCOME_V3_DRAW_FEATURES)
    if not include_topdeck_elo_features:
        excluded_features |= TOPDECK_ELO_DRAW_FEATURES
    base_features = [feature for feature in ALL_DRAW_FEATURES if feature not in excluded_features]
    if feature_set == "default":
        return base_features
    return base_features + list(OUTCOME_V3_DRAW_FEATURES)


def make_xy(rows: list[Any], features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x_matrix = np.asarray([[feature_value(row, feature) for feature in features] for row in rows], dtype=float)
    y_vector = np.asarray([0 if row.is_draw else int(row.winner_index) + 1 for row in rows], dtype=int)
    return x_matrix, y_vector


def empty_pod_row_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in fields(DrawPodRow):
        if field.default is not MISSING:
            payload[field.name] = field.default
        elif field.name == "date":
            payload[field.name] = parse_datetime_value("1970-01-01T00:00:00+00:00")
        elif field.type in (str, "str"):
            payload[field.name] = ""
        else:
            payload[field.name] = 0
    return payload


def rating_features(ratings: list[float]) -> dict[str, float]:
    sorted_ratings = sorted(ratings, reverse=True)
    return {
        "spread": max(ratings) - min(ratings),
        "mean_elo": float(sum(ratings) / len(ratings)),
        "median_elo": float(np.median(np.asarray(ratings, dtype=float))),
        "top2_mean_elo": float(sum(sorted_ratings[:2]) / min(2, len(sorted_ratings))),
        "top3_mean_elo": float(sum(sorted_ratings[:3]) / min(3, len(sorted_ratings))),
        "top1_minus_top2": float(sorted_ratings[0] - sorted_ratings[1]) if len(sorted_ratings) > 1 else 0.0,
        "elo_std": float(np.std(np.asarray(ratings, dtype=float))),
        "elo_gini": 0.0,
        "high1550": sum(1 for rating in ratings if rating >= 1550),
        "high1600": sum(1 for rating in ratings if rating >= 1600),
        "high1650": sum(1 for rating in ratings if rating >= 1650),
        "high1700": sum(1 for rating in ratings if rating >= 1700),
        "high1800": sum(1 for rating in ratings if rating >= 1800),
    }


def fetch_by_game_ids(
    client: SupabaseClient,
    table: str,
    select: str,
    game_ids: list[str],
    *,
    chunk_size: int = 200,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in chunked(game_ids, chunk_size):
        rows.extend(
            fetch_all(
                client,
                table,
                {
                    "select": select,
                    "game_id": f"in.({','.join(chunk)})",
                },
                label=table,
            )
        )
    return rows


def append_top_cut_rows(client: SupabaseClient, pods: list[DrawPodRow]) -> list[DrawPodRow]:
    existing_game_ids = {row.game_id for row in pods}
    max_swiss_round_by_tournament: dict[str, int] = {}
    for row in pods:
        if row.tournament_id and int(row.is_swiss) == 1:
            max_swiss_round_by_tournament[row.tournament_id] = max(
                max_swiss_round_by_tournament.get(row.tournament_id, 0),
                int(row.round_number),
            )

    print("Fetching top-cut game results...", flush=True)
    result_rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": RESULTS_SELECT,
            "result": "neq.bye",
            "round_number": "is.null",
            "order": "start_date.asc,game_id.asc",
        },
        label="top_cut_global_elo_game_results",
    )
    by_game: dict[str, list[dict[str, Any]]] = {}
    for row in result_rows:
        game_id = row.get("game_id")
        if game_id and game_id not in existing_game_ids:
            by_game.setdefault(str(game_id), []).append(row)
    game_ids = sorted(by_game)
    if not game_ids:
        print("No new top-cut games to append.", flush=True)
        return pods

    print(f"Fetching support data for {len(game_ids):,} top-cut games...", flush=True)
    event_rows = fetch_by_game_ids(client, "global_elo_game_events", "game_id,player_id,rating_before", game_ids)
    rating_before = {
        (str(row["game_id"]), str(row["player_id"])): float(row["rating_before"])
        for row in event_rows
        if row.get("game_id") and row.get("player_id") and row.get("rating_before") is not None
    }
    seat_rows = fetch_by_game_ids(client, "game_participants", SEATS_SELECT, game_ids)
    seat_by_pair = {
        (str(row["game_id"]), str(row["entry_id"])): int(row["seat_position"])
        for row in seat_rows
        if row.get("game_id") and row.get("entry_id") and row.get("seat_position") is not None
    }
    tournament_ids = sorted({str(rows[0].get("tournament_id")) for rows in by_game.values() if rows[0].get("tournament_id")})
    tournament_rows: list[dict[str, Any]] = []
    commander_rows: list[dict[str, Any]] = []
    for chunk in chunked(tournament_ids, 200):
        tournament_rows.extend(
            fetch_all(
                client,
                "tournaments",
                {"select": TOURNAMENTS_SELECT, "id": f"in.({','.join(chunk)})"},
                label="top_cut_tournaments",
            )
        )
        commander_rows.extend(
            fetch_all(
                client,
                "tournament_entries",
                {
                    "select": "tournament_id,player_id,commanders(color_identity)",
                    "tournament_id": f"in.({','.join(chunk)})",
                },
                label="top_cut_tournament_entries",
            )
        )
    tournament_meta = {str(row["id"]): row for row in tournament_rows if row.get("id")}
    commander_colors_by_entry = {}
    for row in commander_rows:
        commander = row.get("commanders") or {}
        colors = commander.get("color_identity") or ()
        if row.get("tournament_id") and row.get("player_id"):
            commander_colors_by_entry[(str(row["tournament_id"]), str(row["player_id"]))] = tuple(
                sorted({str(color).upper() for color in colors if color})
            )
    topdeck_elo_rows = fetch_all(
        client,
        "topdeck_player_elos",
        {"select": TOPDECK_ELOS_SELECT},
        label="top_cut_topdeck_player_elos",
    )
    topdeck_elo_by_player_id = {
        str(row["player_id"]): float(row["elo"])
        for row in topdeck_elo_rows
        if row.get("player_id") and row.get("elo") is not None
    }

    appended: list[DrawPodRow] = []
    for game_id, rows in sorted(by_game.items(), key=lambda item: str(item[1][0].get("start_date") or "")):
        tournament_id = str(rows[0].get("tournament_id") or "")
        player_ids = [str(row.get("player_id")) for row in rows if row.get("player_id")]
        ratings = [rating_before.get((game_id, player_id)) for player_id in player_ids]
        if len(player_ids) < 2 or any(rating is None for rating in ratings):
            continue
        if any(str(row.get("result") or "").lower() == "draw" for row in rows):
            continue
        winner_index = next(
            (index for index, row in enumerate(rows) if str(row.get("result") or "").lower() == "win"),
            -1,
        )
        if winner_index < 0:
            continue
        float_ratings = [float(rating) for rating in ratings if rating is not None]
        meta = tournament_meta.get(tournament_id, {})
        tournament_size = int(meta.get("player_count") or len(player_ids))
        top_cut = int(meta.get("top_cut") or 0)
        cut_fraction = min(1.0, top_cut / max(1, tournament_size)) if top_cut > 0 else 0.0
        cut_size_bucket = 0 if top_cut <= 0 else 1 if top_cut <= 4 else 2 if top_cut <= 8 else 3 if top_cut <= 16 else 4 if top_cut <= 32 else 5
        size_bucket = 0 if tournament_size < 32 else 1 if tournament_size < 64 else 2 if tournament_size < 128 else 3
        game_date = parse_datetime_value(rows[0]["start_date"])
        round_number = max_swiss_round_by_tournament.get(tournament_id, 0) + 1
        topdeck_ratings = [topdeck_elo_by_player_id[player_id] for player_id in player_ids if player_id in topdeck_elo_by_player_id]
        commander_color_sets = [commander_colors_by_entry.get((tournament_id, player_id), ()) for player_id in player_ids]
        commander_color_counts = [len(colors) for colors in commander_color_sets]
        unique_commander_colors = {color for colors in commander_color_sets for color in colors}
        seat_positions = [
            seat_by_pair.get((game_id, str(row.get("entry_id")))) if row.get("entry_id") else None
            for row in rows
        ]
        highest_idx = max(range(len(float_ratings)), key=lambda index: float_ratings[index])
        second_idx = sorted(range(len(float_ratings)), key=lambda index: float_ratings[index], reverse=True)[1] if len(float_ratings) > 1 else highest_idx
        seat_highest = seat_positions[highest_idx] if seat_positions[highest_idx] is not None else -1
        seat_second = seat_positions[second_idx] if seat_positions[second_idx] is not None else -1
        payload = empty_pod_row_payload()
        payload.update(
            {
                "game_id": game_id,
                "date": game_date,
                "is_draw": 0,
                "winner_index": winner_index,
                "is_swiss": 0,
                "pod_size": len(player_ids),
                "round_number": round_number,
                "round_name": str(rows[0].get("round_name") or ""),
                "table_number": int(rows[0].get("table_number") or -1),
                "tournament_id": tournament_id,
                "tournament_name": str(meta.get("name") or ""),
                "swiss_progress": 1.0,
                "rounds_remaining": 0,
                "cut_fraction": cut_fraction,
                "cut_size_bucket": cut_size_bucket,
                "month": game_date.month,
                "quarter": ((game_date.month - 1) // 3) + 1,
                "tournament_size": tournament_size,
                "size_bucket": size_bucket,
                "count_currently_in_cut": len(player_ids),
                "round_number_size_bucket": float(round_number * (size_bucket + 1)),
                "round_size_cut_bucket_key": (round_number * 100) + (size_bucket * 10) + cut_size_bucket,
                "pod_size_round_number": float(len(player_ids) * round_number),
                "pod_size_cut_fraction": float(len(player_ids) * cut_fraction),
                "seat_highest": seat_highest,
                "seat_second": seat_second,
                "seat_data_missing": 1 if all(seat is None for seat in seat_positions) else 0,
                "topdeck_elo_spread": float(max(topdeck_ratings) - min(topdeck_ratings)) if len(topdeck_ratings) >= 2 else 0.0,
                "topdeck_elo_mean": float(sum(topdeck_ratings) / len(topdeck_ratings)) if topdeck_ratings else 0.0,
                "topdeck_elo_std": float(np.std(np.asarray(topdeck_ratings, dtype=float))) if topdeck_ratings else 0.0,
                "topdeck_elo_missing_count": len(player_ids) - len(topdeck_ratings),
                "count_white_commanders": sum(1 for colors in commander_color_sets if "W" in colors),
                "count_blue_commanders": sum(1 for colors in commander_color_sets if "U" in colors),
                "count_black_commanders": sum(1 for colors in commander_color_sets if "B" in colors),
                "count_red_commanders": sum(1 for colors in commander_color_sets if "R" in colors),
                "count_green_commanders": sum(1 for colors in commander_color_sets if "G" in colors),
                "avg_commander_color_count": float(sum(commander_color_counts) / len(commander_color_counts)) if commander_color_counts else 0.0,
                "max_commander_color_count": max(commander_color_counts) if commander_color_counts else 0,
                "unique_commander_color_count": len(unique_commander_colors),
                "commander_color_data_missing_count": sum(1 for colors in commander_color_sets if not colors),
            }
        )
        payload.update(rating_features(float_ratings))
        payload["topdeck_elo_minus_internal_mean"] = payload["topdeck_elo_mean"] - payload["mean_elo"] if topdeck_ratings else 0.0
        appended.append(DrawPodRow(**payload))

    print(f"Appended {len(appended):,} top-cut pod rows.", flush=True)
    return pods + appended


def score_multiclass(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    clipped = np.clip(probabilities.astype(float), 1e-9, 1.0)
    clipped = clipped / clipped.sum(axis=1, keepdims=True)
    labels = y_true.astype(int)
    log_loss = float(np.mean(-np.log(clipped[np.arange(len(labels)), labels])))
    brier = float(np.mean(np.sum((clipped - np.eye(clipped.shape[1])[labels]) ** 2, axis=1)))
    draw_probability = clipped[:, 0]
    draw_log_loss, draw_brier = score_probs((labels == 0).astype(int), draw_probability)
    decisive_mask = labels != 0
    winner_log_loss = (
        float(np.mean(-np.log(clipped[decisive_mask, labels[decisive_mask]])))
        if np.any(decisive_mask)
        else 0.0
    )
    return {
        "log_loss": log_loss,
        "brier": brier,
        "draw_log_loss": draw_log_loss,
        "draw_brier": draw_brier,
        "winner_log_loss": winner_log_loss,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument(
        "--append-top-cut-games",
        action="store_true",
        help="Load the existing rich cache, fetch only missing top-cut/bracket games, append them, and save the cache.",
    )
    parser.add_argument(
        "--raw-data-cache-dir",
        help="Optional directory for cached raw Supabase table snapshots used while rebuilding the rich pod cache.",
    )
    parser.add_argument("--half-life", type=int, default=90)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    parser.add_argument("--max-train-rows", type=int, help="Use only the newest N training rows for quick experiments.")
    parser.add_argument("--feature-set", choices=("default", "v3"), default="v3")
    parser.add_argument(
        "--include-topdeck-elo-features",
        action="store_true",
        help="Include displayed TopDeck Elo features. Off by default; internal Elo remains the normal predictive input.",
    )
    args = parser.parse_args()

    load_local_env()
    cache_path = Path(args.cache_path)
    artifact_path = Path(args.artifact_path)
    report_path = Path(args.report_path)
    raw_data_cache_dir = Path(args.raw_data_cache_dir) if args.raw_data_cache_dir else None

    pods = None if args.rebuild_cache else load_pods(cache_path)
    if pods is None:
        client = SupabaseClient(
            url=os.environ["SUPABASE_URL"],
            service_key=os.environ["SUPABASE_SERVICE_KEY"],
        )
        pods = build_rich_pod_cache(client, raw_data_cache_dir=raw_data_cache_dir)
        save_pods(cache_path, pods)
        print(f"Built and cached rich pod dataset: {len(pods):,} pods", flush=True)
    else:
        print(f"Loaded rich cache: {len(pods):,} pods", flush=True)
    if args.append_top_cut_games:
        client = SupabaseClient(
            url=os.environ["SUPABASE_URL"],
            service_key=os.environ["SUPABASE_SERVICE_KEY"],
        )
        updated_pods = append_top_cut_rows(client, pods)
        if len(updated_pods) != len(pods):
            save_pods(cache_path, updated_pods)
            print(f"Saved appended rich cache: {len(updated_pods):,} pods", flush=True)
        pods = updated_pods

    rows = [
        row
        for row in pods
        if 2 <= int(row.pod_size) <= 4 and (int(row.is_draw) == 1 or 0 <= int(row.winner_index) < int(row.pod_size))
    ]
    if not rows:
        raise RuntimeError("No trainable pod outcome rows found. Rebuild the cache so winner_index is populated.")

    count = len(rows)
    train_end = int(count * (1.0 - args.test_fraction))
    train_rows = rows[:train_end]
    test_rows = rows[train_end:]
    if args.max_train_rows and args.max_train_rows > 0 and len(train_rows) > args.max_train_rows:
        train_rows = train_rows[-args.max_train_rows :]
    features = select_outcome_features(
        args.feature_set,
        include_topdeck_elo_features=args.include_topdeck_elo_features,
    )
    params = {
        "learning_rate": 0.08,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 250,
        "max_depth": None,
        "l2_regularization": 0.0,
    }
    selection = OutcomeModelSelection(
        feature_set_name=f"full_outcome_{args.feature_set}",
        features=features,
        half_life=args.half_life,
        learning_rate=float(params["learning_rate"]),
        max_leaf_nodes=int(params["max_leaf_nodes"]),
        min_samples_leaf=int(params["min_samples_leaf"]),
        max_depth=params["max_depth"],
        l2_regularization=float(params["l2_regularization"]),
    )

    x_train, y_train = make_xy(train_rows, features)
    x_test, y_test = make_xy(test_rows, features)
    sample_weight = np.asarray(
        [recency_weight(row.date, train_rows[-1].date, args.half_life) for row in train_rows],
        dtype=float,
    )
    model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **params)
    model.fit(x_train, y_train, sample_weight=sample_weight)
    probabilities = model.predict_proba(x_test)
    holdout = score_multiclass(y_test, probabilities)

    artifact = {
        "target": "pod_outcome",
        "selection": asdict(selection),
        "model": model,
        "calibration": "uncalibrated",
        "calibrator": None,
        "classes": [int(value) for value in model.classes_],
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("wb") as handle:
        pickle.dump(artifact, handle)

    report = {
        "target": "pod_outcome",
        "selection": asdict(selection),
        "rows": {"train": len(train_rows), "test": len(test_rows), "total": len(rows)},
        "features": {
            "count": len(features),
            "feature_set": args.feature_set,
            "outcome_v3_feature_count": len([feature for feature in features if feature in OUTCOME_V3_DRAW_FEATURES]),
            "include_topdeck_elo_features": bool(args.include_topdeck_elo_features),
        },
        "round_type_counts": {
            "swiss": sum(1 for row in rows if int(row.is_swiss) == 1),
            "top_cut": sum(1 for row in rows if int(row.is_swiss) == 0),
        },
        "class_counts": {
            str(class_label): int(count)
            for class_label, count in zip(*np.unique(np.asarray([0 if row.is_draw else int(row.winner_index) + 1 for row in rows]), return_counts=True), strict=True)
        },
        "holdout": holdout,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
