#!/usr/bin/env python3
"""Run targeted draw-model weighting experiments against the v8 baseline."""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier


@dataclass(frozen=True)
class WeightConfig:
    name: str
    rr1_mult: float = 1.0
    rr2_mult: float = 1.0
    size_64_127_mult: float = 1.0
    size_128_255_mult: float = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", required=True)
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


def parse_date(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def score_probs(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, float]:
    clipped = np.clip(probabilities.astype(float), 1e-6, 1 - 1e-6)
    labels = y_true.astype(float)
    log_loss = float(np.mean(-(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped))))
    brier = float(np.mean((clipped - labels) ** 2))
    return log_loss, brier


def recency_weight(game_date: datetime, reference_date: datetime, half_life: int) -> float:
    age_days = max(0.0, (reference_date - game_date).total_seconds() / 86_400.0)
    return 0.5 ** (age_days / half_life)


def make_xy(rows: list[dict[str, Any]], features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x_matrix = np.asarray([[row[feature] for feature in features] for row in rows], dtype=float)
    y_vector = np.asarray([int(row["is_draw"]) for row in rows], dtype=int)
    return x_matrix, y_vector


def weight_multiplier(row: dict[str, Any], config: WeightConfig) -> float:
    multiplier = 1.0
    rounds_remaining = int(row["rounds_remaining"])
    tournament_size = int(row["tournament_size"])
    if rounds_remaining == 1:
        multiplier *= config.rr1_mult
    elif rounds_remaining == 2:
        multiplier *= config.rr2_mult
    if 64 <= tournament_size <= 127:
        multiplier *= config.size_64_127_mult
    elif 128 <= tournament_size <= 255:
        multiplier *= config.size_128_255_mult
    return multiplier


def slice_bucket(row: dict[str, Any]) -> str:
    rounds_remaining = int(row["rounds_remaining"])
    tournament_size = int(row["tournament_size"])
    if rounds_remaining <= 1:
        rr_bucket = "1"
    elif rounds_remaining == 2:
        rr_bucket = "2"
    elif rounds_remaining <= 4:
        rr_bucket = "3-4"
    else:
        rr_bucket = "5+"
    if tournament_size < 64:
        size_bucket = "<64"
    elif tournament_size < 128:
        size_bucket = "64-127"
    elif tournament_size < 256:
        size_bucket = "128-255"
    else:
        size_bucket = "256+"
    return f"{rr_bucket} | {size_bucket}"


def evaluate_slices(
    rows: list[dict[str, Any]],
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        grouped.setdefault(slice_bucket(row), []).append(index)
    metrics: dict[str, dict[str, float]] = {}
    for bucket, indices in sorted(grouped.items()):
        ys = y_true[indices]
        ps = probabilities[indices]
        log_loss, brier = score_probs(ys, ps)
        metrics[bucket] = {
            "cases": len(indices),
            "log_loss": log_loss,
            "brier": brier,
            "draw_rate": float(np.mean(ys)),
            "predicted_draw_rate": float(np.mean(ps)),
        }
    return metrics


def main() -> None:
    args = parse_args()
    with Path(args.report_path).open() as handle:
        report = json.load(handle)
    with Path(args.cache_path).open("rb") as handle:
        rows: list[dict[str, Any]] = pickle.load(handle)

    selection = report["selection"]
    features = list(selection["features"])
    half_life = int(selection["half_life"])
    model_params = {
        "learning_rate": float(selection["learning_rate"]),
        "max_leaf_nodes": int(selection["max_leaf_nodes"]),
        "min_samples_leaf": int(selection["min_samples_leaf"]),
        "max_depth": selection["max_depth"],
        "l2_regularization": float(selection["l2_regularization"]),
    }

    count = len(rows)
    development_end = int(count * 0.8)
    train_end = int(count * 0.7)
    train_rows = rows[:train_end]
    test_rows = rows[development_end:]
    reference_date = parse_date(train_rows[-1]["date"])

    x_train, y_train = make_xy(train_rows, features)
    x_test, y_test = make_xy(test_rows, features)

    experiments = [
        WeightConfig("baseline"),
        WeightConfig("rr2_1.10", rr2_mult=1.10),
        WeightConfig("rr2_1.20", rr2_mult=1.20),
        WeightConfig("midsize_1.10", size_64_127_mult=1.10, size_128_255_mult=1.10),
        WeightConfig("midsize_1.20", size_64_127_mult=1.20, size_128_255_mult=1.20),
        WeightConfig("rr2_1.10_midsize_1.10", rr2_mult=1.10, size_64_127_mult=1.10, size_128_255_mult=1.10),
        WeightConfig("rr2_1.20_midsize_1.10", rr2_mult=1.20, size_64_127_mult=1.10, size_128_255_mult=1.10),
        WeightConfig("rr2_1.10_mid64_1.20_mid128_1.10", rr2_mult=1.10, size_64_127_mult=1.20, size_128_255_mult=1.10),
        WeightConfig("rr1_1.05_rr2_1.15_midsize_1.10", rr1_mult=1.05, rr2_mult=1.15, size_64_127_mult=1.10, size_128_255_mult=1.10),
        WeightConfig("rr1_1.05_rr2_1.20_midsize_1.15", rr1_mult=1.05, rr2_mult=1.20, size_64_127_mult=1.15, size_128_255_mult=1.15),
    ]

    results: list[dict[str, Any]] = []
    best_entry: dict[str, Any] | None = None

    for config in experiments:
        sample_weight = np.asarray(
            [
                recency_weight(parse_date(row["date"]), reference_date, half_life) * weight_multiplier(row, config)
                for row in train_rows
            ],
            dtype=float,
        )
        model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **model_params)
        model.fit(x_train, y_train, sample_weight=sample_weight)
        probabilities = model.predict_proba(x_test)[:, 1]
        log_loss, brier = score_probs(y_test, probabilities)
        entry = {
            "name": config.name,
            "weights": {
                "rr1_mult": config.rr1_mult,
                "rr2_mult": config.rr2_mult,
                "size_64_127_mult": config.size_64_127_mult,
                "size_128_255_mult": config.size_128_255_mult,
            },
            "holdout": {
                "test_log_loss": log_loss,
                "test_brier": brier,
            },
            "slice_metrics": evaluate_slices(test_rows, y_test, probabilities),
        }
        print(json.dumps({"name": config.name, "test_log_loss": log_loss, "test_brier": brier}), flush=True)
        results.append(entry)
        if best_entry is None or (
            entry["holdout"]["test_log_loss"],
            entry["holdout"]["test_brier"],
        ) < (
            best_entry["holdout"]["test_log_loss"],
            best_entry["holdout"]["test_brier"],
        ):
            best_entry = entry

    baseline = next(item for item in results if item["name"] == "baseline")
    output = {
        "source_report": str(Path(args.report_path)),
        "source_cache": str(Path(args.cache_path)),
        "baseline_holdout": baseline["holdout"],
        "best": best_entry,
        "results": sorted(results, key=lambda item: (item["holdout"]["test_log_loss"], item["holdout"]["test_brier"])),
    }
    Path(args.output_path).write_text(json.dumps(output, indent=2) + "\n")
    print(f"Wrote experiment report to {args.output_path}", flush=True)


if __name__ == "__main__":
    main()
