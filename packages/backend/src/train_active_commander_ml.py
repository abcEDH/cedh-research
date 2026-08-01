#!/usr/bin/env python3
"""Train an offline ML challenger for active-commander prediction.

This script intentionally does not write production data. It builds the same
historical next-commander targets as the active-commander backtest, trains a
candidate-level binary classifier on older targets, and compares the normalized
candidate probabilities against the current production baseline on newer
targets.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import date, datetime, time
from typing import Any

import numpy as np
import psycopg2
import psycopg2.extras
from dateutil import parser as date_parser
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import backtest_active_commander_model as baseline

FEATURE_NAMES = [
    "current_share",
    "production_share",
    "hybrid_share",
    "latest_bonus",
    "entries",
    "total_entries",
    "distinct_prior_tournaments",
    "selected_entries",
    "lifetime_share",
    "selected_share",
    "days_since_commander_last_played",
    "days_since_player_last_played",
    "same_as_latest_two",
    "has_recent_decklist",
    "commander_last_played_recency",
    "hidden_elo_before",
    "hidden_elo_games_before",
    "hidden_elo_above_1500",
]


def _target_datetime(example: dict[str, Any]) -> datetime:
    return datetime.combine(example["target_date"], time.min, tzinfo=baseline.UTC)


def _days_between(target: datetime, value: Any) -> float:
    parsed = baseline.parse_start_datetime(value)
    if parsed is None:
        return 9999.0
    return float(max(0, (target - parsed).days))


def _selected_rows(history_rows: list[dict[str, Any]], reference_date: date) -> list[dict[str, Any]]:
    rows_by_topdeck_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history_rows:
        rows_by_topdeck_id[row["topdeck_id"]].append(row)
    topdeck_id = history_rows[0]["topdeck_id"] if history_rows else ""
    return baseline.select_commander_forecast_rows(rows_by_topdeck_id, reference_date).get(topdeck_id, [])


def build_candidate_rows(example: dict[str, Any]) -> list[dict[str, Any]]:
    history_rows = example["history_rows"]
    if not history_rows:
        return []

    reference_date = example["target_date"]
    target_dt = _target_datetime(example)
    current_dist = baseline.current_profile_distribution(history_rows, reference_date)
    production_dist = baseline.production_distribution(history_rows, reference_date)
    hybrid_dist = baseline.hybrid_distribution(history_rows, reference_date)
    latest_dist = baseline.latest_known_distribution(history_rows)
    selected_rows = _selected_rows(history_rows, reference_date)

    lifetime_counts: dict[str, int] = defaultdict(int)
    selected_counts: dict[str, int] = defaultdict(int)
    latest_date_by_commander: dict[str, str] = {}
    recent_decklist_by_commander: dict[str, bool] = defaultdict(bool)
    for row in history_rows:
        commander = baseline.commander_from_row(row)
        if not commander:
            continue
        lifetime_counts[commander] += 1
        start_date = row.get("start_date") or ""
        if start_date > latest_date_by_commander.get(commander, ""):
            latest_date_by_commander[commander] = start_date
        if row.get("decklist_url") or row.get("topdeck_decklist_url"):
            if _days_between(target_dt, start_date) <= 120:
                recent_decklist_by_commander[commander] = True

    for row in selected_rows:
        commander = baseline.commander_from_row(row)
        if commander:
            selected_counts[commander] += 1

    sorted_history = sorted(history_rows, key=lambda row: row.get("start_date") or "", reverse=True)
    latest_two = [baseline.commander_from_row(row) for row in sorted_history[:2]]
    repeat_latest = latest_two[0] if len(latest_two) >= 2 and latest_two[0] == latest_two[1] else None
    player_last_played = sorted_history[0].get("start_date") if sorted_history else None
    days_since_player_last_played = _days_between(target_dt, player_last_played)
    total_entries = sum(lifetime_counts.values())
    distinct_prior_tournaments = len(
        {
            row.get("tournament_id")
            for row in history_rows
            if row.get("tournament_id")
        }
    )
    total_selected = sum(selected_counts.values())
    hidden_elo_before = float(example.get("hidden_elo_before") or 1500.0)
    hidden_elo_games_before = float(example.get("hidden_elo_games_before") or 0.0)
    candidates = sorted(set(lifetime_counts) | set(current_dist) | set(production_dist) | set(hybrid_dist))

    rows: list[dict[str, Any]] = []
    for commander in candidates:
        commander_days = _days_between(target_dt, latest_date_by_commander.get(commander))
        features = [
            current_dist.get(commander, 0.0),
            production_dist.get(commander, 0.0),
            hybrid_dist.get(commander, 0.0),
            latest_dist.get(commander, 0.0),
            float(lifetime_counts.get(commander, 0)),
            float(total_entries),
            float(distinct_prior_tournaments),
            float(selected_counts.get(commander, 0)),
            lifetime_counts.get(commander, 0) / total_entries if total_entries else 0.0,
            selected_counts.get(commander, 0) / total_selected if total_selected else 0.0,
            commander_days,
            days_since_player_last_played,
            1.0 if commander == repeat_latest else 0.0,
            1.0 if recent_decklist_by_commander.get(commander) else 0.0,
            math.exp(-commander_days / 90.0),
            hidden_elo_before,
            hidden_elo_games_before,
            hidden_elo_before - 1500.0,
        ]
        rows.append(
            {
                "commander": commander,
                "features": features,
                "label": 1 if commander == example["actual"] else 0,
            }
        )
    return rows


def split_examples_by_time(
    examples: list[dict[str, Any]],
    *,
    train_fraction: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sorted_examples = sorted(examples, key=lambda row: (row["target_date"], row["topdeck_id"]))
    split_index = max(1, min(len(sorted_examples) - 1, int(len(sorted_examples) * train_fraction)))
    return sorted_examples[:split_index], sorted_examples[split_index:]


def _chunked(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def fetch_hidden_elo_events_for_examples(
    db_url: str,
    examples: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    player_ids = sorted(
        {
            row.get("player_id")
            for example in examples
            for row in example.get("history_rows", [])
            if row.get("player_id")
        }
    )
    if not player_ids:
        return {}
    max_target_date = max(example["target_date"] for example in examples)
    sql = """
        SELECT player_id, game_date, rating_before, rating_after
        FROM global_elo_game_events
        WHERE region_type = 'global'
          AND region_key = 'ALL'
          AND player_id = ANY(%s::uuid[])
          AND game_date < %s
        ORDER BY player_id ASC, game_date ASC
    """
    events_by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with psycopg2.connect(db_url, connect_timeout=15) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            for chunk in _chunked(player_ids, 1000):
                cursor.execute(sql, (chunk, datetime.combine(max_target_date, time.min, tzinfo=baseline.UTC)))
                for row in cursor.fetchall():
                    events_by_player[str(row["player_id"])].append(dict(row))
    return events_by_player


def enrich_examples_with_hidden_elo(
    examples: list[dict[str, Any]],
    events_by_player: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    event_offsets: dict[str, int] = defaultdict(int)
    rating_by_player: dict[str, float] = defaultdict(lambda: 1500.0)
    games_by_player: dict[str, int] = defaultdict(int)
    sorted_examples = sorted(examples, key=lambda row: (row["target_date"], row["topdeck_id"]))
    for example in sorted_examples:
        player_id = next(
            (row.get("player_id") for row in example.get("history_rows", []) if row.get("player_id")),
            None,
        )
        target_dt = datetime.combine(example["target_date"], time.min, tzinfo=baseline.UTC)
        hidden_elo_before = rating_by_player[str(player_id)] if player_id else 1500.0
        hidden_elo_games_before = games_by_player[str(player_id)] if player_id else 0
        if player_id:
            player_events = events_by_player.get(str(player_id), [])
            offset = event_offsets[str(player_id)]
            while offset < len(player_events):
                event_date = baseline.parse_start_datetime(player_events[offset].get("game_date"))
                if event_date is None or event_date >= target_dt:
                    break
                rating = player_events[offset].get("rating_before")
                if rating is not None:
                    hidden_elo_before = float(rating)
                rating_after = player_events[offset].get("rating_after")
                if rating_after is not None:
                    hidden_elo_before = float(rating_after)
                hidden_elo_games_before += 1
                offset += 1
            event_offsets[str(player_id)] = offset
            rating_by_player[str(player_id)] = hidden_elo_before
            games_by_player[str(player_id)] = hidden_elo_games_before
        enriched.append(
            {
                **example,
                "hidden_elo_before": hidden_elo_before,
                "hidden_elo_games_before": hidden_elo_games_before,
            }
        )
    return enriched


def train_model(train_examples: list[dict[str, Any]], model_type: str):
    feature_rows: list[list[float]] = []
    labels: list[int] = []
    skipped_without_positive = 0
    for example in train_examples:
        rows = build_candidate_rows(example)
        if not any(row["label"] for row in rows):
            skipped_without_positive += 1
            continue
        for row in rows:
            feature_rows.append(row["features"])
            labels.append(row["label"])

    if len(set(labels)) < 2:
        raise ValueError("Training data must contain both positive and negative candidate rows")

    if model_type == "hist_gradient_boosting":
        model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=200,
            l2_regularization=0.05,
            random_state=17,
        )
    elif model_type == "logistic":
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", random_state=17),
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")

    model.fit(np.asarray(feature_rows, dtype=float), np.asarray(labels, dtype=int))
    return model, {
        "candidate_rows": len(feature_rows),
        "positive_rows": sum(labels),
        "skipped_examples_without_positive_candidate": skipped_without_positive,
    }


def predict_ml_distribution(model: Any, example: dict[str, Any]) -> dict[str, float]:
    rows = build_candidate_rows(example)
    if not rows:
        return {}
    features = np.asarray([row["features"] for row in rows], dtype=float)
    probabilities = model.predict_proba(features)[:, 1]
    scores = {
        row["commander"]: float(max(probability, baseline.EPSILON))
        for row, probability in zip(rows, probabilities, strict=True)
    }
    return baseline.normalize_scores(scores)


def evaluate_model_on_examples(model: Any, examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for example in examples:
        distribution = predict_ml_distribution(model, example)
        results.append({**baseline.evaluate_prediction(distribution, example["actual"]), "example": example})
    return results


def blend_distributions(
    left: dict[str, float],
    right: dict[str, float],
    *,
    right_weight: float,
) -> dict[str, float]:
    commanders = set(left) | set(right)
    return baseline.normalize_scores(
        {
            commander: (1 - right_weight) * left.get(commander, 0.0) + right_weight * right.get(commander, 0.0)
            for commander in commanders
        }
    )


def ensemble_sweep(model: Any, examples: list[dict[str, Any]], weights: list[float]) -> dict[str, dict[str, Any]]:
    results_by_weight: dict[str, list[dict[str, Any]]] = {f"ml_weight_{weight:.2f}": [] for weight in weights}
    for example in examples:
        production = baseline.production_distribution(example["history_rows"], example["target_date"])
        ml_distribution = predict_ml_distribution(model, example)
        for weight in weights:
            distribution = blend_distributions(production, ml_distribution, right_weight=weight)
            results_by_weight[f"ml_weight_{weight:.2f}"].append(
                baseline.evaluate_prediction(distribution, example["actual"])
            )
    return {name: baseline.summarize_results(results) for name, results in results_by_weight.items()}


def run_ml_backtest(
    examples: list[dict[str, Any]],
    *,
    model_type: str,
    train_fraction: float,
) -> dict[str, Any]:
    train_examples, test_examples = split_examples_by_time(examples, train_fraction=train_fraction)
    model, train_info = train_model(train_examples, model_type)
    ml_results = evaluate_model_on_examples(model, test_examples)
    production_results = [
        baseline.evaluate_prediction(
            baseline.production_distribution(example["history_rows"], example["target_date"]),
            example["actual"],
        )
        for example in test_examples
    ]
    current_results = [
        baseline.evaluate_prediction(
            baseline.current_profile_distribution(example["history_rows"], example["target_date"]),
            example["actual"],
        )
        for example in test_examples
    ]
    test_dates = [example["target_date"] for example in test_examples]
    output = {
        "examples": len(examples),
        "train_examples": len(train_examples),
        "test_examples": len(test_examples),
        "test_start_date": min(test_dates).isoformat() if test_dates else None,
        "test_end_date": max(test_dates).isoformat() if test_dates else None,
        "model_type": model_type,
        "features": FEATURE_NAMES,
        "train": train_info,
        "summary": {
            "current": baseline.summarize_results(current_results),
            "production": baseline.summarize_results(production_results),
            f"ml_{model_type}": baseline.summarize_results(ml_results),
        },
        "ensemble_sweep": ensemble_sweep(
            model,
            test_examples,
            [round(weight / 100, 2) for weight in range(0, 101, 10)],
        ),
        "bucket_report": baseline.run_bucket_backtest(
            test_examples,
            predict=lambda history, ref_date: predict_ml_distribution(
                model,
                {"history_rows": history, "target_date": ref_date, "actual": ""},
            ),
        ),
    }
    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get("logisticregression")
        if estimator is not None:
            output["feature_weights"] = dict(
                sorted(
                    zip(FEATURE_NAMES, estimator.coef_[0].tolist(), strict=True),
                    key=lambda item: abs(item[1]),
                    reverse=True,
                )
            )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an active-commander ML challenger")
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--since", type=str, default="2025-01-01")
    parser.add_argument("--limit-targets", type=int)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument(
        "--no-hidden-elo",
        action="store_true",
        help="Do not fetch historical hidden Elo features from global_elo_game_events",
    )
    parser.add_argument(
        "--model",
        choices=["logistic", "hist_gradient_boosting"],
        default="logistic",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    since = date_parser.parse(args.since).date() if args.since else None
    usage_rows = baseline.load_usage_rows(since=since, limit_targets=args.limit_targets)
    examples = baseline.build_backtest_examples(
        usage_rows,
        min_history=args.min_history,
        since=since,
        limit_targets=args.limit_targets,
    )
    if not args.no_hidden_elo and os.environ.get("SUPABASE_DB_URL"):
        elo_events = fetch_hidden_elo_events_for_examples(os.environ["SUPABASE_DB_URL"], examples)
        examples = enrich_examples_with_hidden_elo(examples, elo_events)
    result = run_ml_backtest(
        examples,
        model_type=args.model,
        train_fraction=args.train_fraction,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    print(
        f"Trained {result['model_type']} on {result['train_examples']} examples; "
        f"tested on {result['test_examples']} examples "
        f"({result['test_start_date']} to {result['test_end_date']})"
    )
    print(
        "Training rows: "
        f"{result['train']['candidate_rows']} candidates, "
        f"{result['train']['positive_rows']} positives, "
        f"{result['train']['skipped_examples_without_positive_candidate']} skipped targets"
    )
    print("model                 targets  top1     top3     log_loss")
    for model_name, summary in result["summary"].items():
        print(
            f"{model_name:<21} {summary['targets']:>7}  "
            f"{summary['top1_accuracy']:.3f}  {summary['top3_accuracy']:.3f}  {summary['log_loss']:.3f}"
        )
    print()
    print("production/ml ensemble sweep")
    print("ml weight             targets  top1     top3     log_loss")
    for model_name, summary in result["ensemble_sweep"].items():
        weight = model_name.removeprefix("ml_weight_")
        print(
            f"{weight:<21} {summary['targets']:>7}  "
            f"{summary['top1_accuracy']:.3f}  {summary['top3_accuracy']:.3f}  {summary['log_loss']:.3f}"
        )
    if result.get("feature_weights"):
        print()
        print("largest logistic weights")
        for name, weight in list(result["feature_weights"].items())[:10]:
            print(f"{name:<36} {weight: .4f}")


if __name__ == "__main__":
    main()
