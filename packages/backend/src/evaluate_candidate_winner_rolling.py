#!/usr/bin/env python3
"""Run a rolling month-by-month backtest for the candidate winner model."""

from __future__ import annotations

import argparse
import json
import math
import pickle
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from train_draw_model import DEFAULT_CACHE_PATH

from evaluate_candidate_winner_model import (
    CandidateExample,
    build_candidate_examples,
    candidate_scores_by_game,
    fit_candidate_model,
    fit_draw_model,
    row_segment_keys,
)
from evaluate_pod_outcome_vs_draw_elo import (
    EPSILON,
    is_valid_outcome_row,
    load_cached_rows,
    make_x as make_pod_x,
    predict_draw_probability,
    row_date,
    row_value,
    select_features,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_PARTICIPANT_CACHE_PATH = DATA_DIR / "candidate_winner_eval_participants.pkl"
DEFAULT_REPORT_PATH = DATA_DIR / "candidate_winner_rolling_eval.json"


@dataclass(frozen=True)
class ScoredRow:
    old_probability: float
    candidate_probability: float
    segment_keys: tuple[str, ...]


def month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def parse_month(value: str) -> tuple[int, int]:
    year_text, month_text = value.split("-", 1)
    return int(year_text), int(month_text)


def month_sort_key(value: str) -> tuple[int, int]:
    return parse_month(value)


def load_participant_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing participant cache: {path}. Run evaluate_candidate_winner_model.py first."
        )
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if "payload" in payload:
        return payload["payload"]
    return payload


def log_loss(probabilities: list[float]) -> float:
    return float(np.mean([-math.log(max(EPSILON, min(1.0, value))) for value in probabilities])) if probabilities else 0.0


def summarize_scored_rows(rows: list[ScoredRow]) -> dict[str, Any]:
    by_segment: dict[str, list[ScoredRow]] = defaultdict(list)
    for row in rows:
        for key in row.segment_keys:
            by_segment[key].append(row)
    preferred = [
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
    keys = [key for key in preferred if key in by_segment] + sorted(key for key in by_segment if key not in preferred)
    summary: dict[str, Any] = {}
    for key in keys:
        segment_rows = by_segment[key]
        old_loss = log_loss([row.old_probability for row in segment_rows])
        candidate_loss = log_loss([row.candidate_probability for row in segment_rows])
        summary[key] = {
            "rows": len(segment_rows),
            "old_draw_plus_elo_log_loss": old_loss,
            "candidate_winner_log_loss": candidate_loss,
            "delta_candidate_minus_old": candidate_loss - old_loss,
        }
    return summary


def winner_and_elo_shares(examples: list[CandidateExample]) -> tuple[dict[str, str], dict[str, dict[str, float]]]:
    from evaluate_candidate_winner_model import CANDIDATE_FEATURES

    share_index = CANDIDATE_FEATURES.index("candidate_elo_share")
    winners: dict[str, str] = {}
    shares: dict[str, dict[str, float]] = defaultdict(dict)
    for example in examples:
        shares[example.game_id][example.player_id] = float(example.features[share_index])
        if example.label == 1:
            winners[example.game_id] = example.player_id
    return winners, shares


def score_fold(
    *,
    train_rows: list[Any],
    test_rows: list[Any],
    candidate_examples_by_game: dict[str, list[CandidateExample]],
    winners_by_game: dict[str, str],
    elo_shares_by_game: dict[str, dict[str, float]],
    pod_features: list[str],
) -> tuple[list[ScoredRow], dict[str, Any]]:
    train_game_ids = {str(row_value(row, "game_id", "") or "") for row in train_rows}
    test_game_ids = {str(row_value(row, "game_id", "") or "") for row in test_rows}
    train_candidate_examples = [
        example
        for game_id in train_game_ids
        for example in candidate_examples_by_game.get(game_id, ())
    ]
    test_candidate_examples = [
        example
        for game_id in test_game_ids
        for example in candidate_examples_by_game.get(game_id, ())
    ]
    if not train_candidate_examples or not test_rows:
        return [], {
            "train_candidate_examples": len(train_candidate_examples),
            "test_candidate_examples": len(test_candidate_examples),
        }

    draw_model = fit_draw_model(train_rows, pod_features)
    candidate_model = fit_candidate_model(train_candidate_examples)
    draw_probabilities = predict_draw_probability(draw_model, make_pod_x(test_rows, pod_features)).tolist()
    candidate_shares_by_game = candidate_scores_by_game(candidate_model, test_candidate_examples)

    scored: list[ScoredRow] = []
    for row, draw_probability in zip(test_rows, draw_probabilities, strict=True):
        game_id = str(row_value(row, "game_id", "") or "")
        is_draw = int(row_value(row, "is_draw", 0)) == 1
        is_swiss = int(row_value(row, "is_swiss", 0)) == 1
        if is_draw:
            actual_probability = draw_probability if is_swiss else 0.0
            scored.append(
                ScoredRow(
                    old_probability=actual_probability,
                    candidate_probability=actual_probability,
                    segment_keys=row_segment_keys(row),
                )
            )
            continue
        winner_id = winners_by_game.get(game_id)
        if not winner_id:
            continue
        decisive_probability = 1.0 - draw_probability if is_swiss else 1.0
        old_probability = decisive_probability * elo_shares_by_game.get(game_id, {}).get(winner_id, 0.0)
        candidate_probability = decisive_probability * candidate_shares_by_game.get(game_id, {}).get(winner_id, 0.0)
        scored.append(
            ScoredRow(
                old_probability=old_probability,
                candidate_probability=candidate_probability,
                segment_keys=row_segment_keys(row),
            )
        )
    metadata = {
        "train_candidate_examples": len(train_candidate_examples),
        "test_candidate_examples": len(test_candidate_examples),
    }
    return scored, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--participant-cache-path", default=str(DEFAULT_PARTICIPANT_CACHE_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--last-months", type=int, default=8)
    parser.add_argument("--start-month", help="First YYYY-MM month to evaluate. Overrides --last-months.")
    parser.add_argument("--end-month", help="Last YYYY-MM month to evaluate.")
    parser.add_argument("--min-train-rows", type=int, default=50_000)
    args = parser.parse_args()

    started = time.perf_counter()
    rows = [
        row
        for row in load_cached_rows(Path(args.cache_path))
        if is_valid_outcome_row(row) and row_value(row, "tournament_id")
    ]
    participant_payload = load_participant_payload(Path(args.participant_cache_path))
    print("Building candidate examples from cached participant/Elo data...", flush=True)
    all_candidate_examples = build_candidate_examples(rows, participant_payload)
    candidate_examples_by_game: dict[str, list[CandidateExample]] = defaultdict(list)
    for example in all_candidate_examples:
        candidate_examples_by_game[example.game_id].append(example)
    winners_by_game, elo_shares_by_game = winner_and_elo_shares(all_candidate_examples)

    rows_by_month: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        rows_by_month[month_key(row_date(row))].append(row)
    months = sorted(rows_by_month, key=month_sort_key)
    candidate_months = [
        value
        for value in months
        if len([row for month in months if month_sort_key(month) < month_sort_key(value) for row in rows_by_month[month]])
        >= args.min_train_rows
    ]
    if args.start_month:
        candidate_months = [month for month in candidate_months if month_sort_key(month) >= month_sort_key(args.start_month)]
    elif args.last_months and args.last_months > 0:
        candidate_months = candidate_months[-args.last_months :]
    if args.end_month:
        candidate_months = [month for month in candidate_months if month_sort_key(month) <= month_sort_key(args.end_month)]
    if not candidate_months:
        raise RuntimeError("No months selected for rolling evaluation")

    pod_features = select_features(include_topdeck_elo_features=False)
    folds: list[dict[str, Any]] = []
    all_scored: list[ScoredRow] = []
    for index, test_month in enumerate(candidate_months, start=1):
        train_rows = [
            row
            for month in months
            if month_sort_key(month) < month_sort_key(test_month)
            for row in rows_by_month[month]
        ]
        test_rows = rows_by_month[test_month]
        print(
            f"[{index}/{len(candidate_months)}] {test_month}: train_rows={len(train_rows):,} test_rows={len(test_rows):,}",
            flush=True,
        )
        scored_rows, metadata = score_fold(
            train_rows=train_rows,
            test_rows=test_rows,
            candidate_examples_by_game=candidate_examples_by_game,
            winners_by_game=winners_by_game,
            elo_shares_by_game=elo_shares_by_game,
            pod_features=pod_features,
        )
        all_scored.extend(scored_rows)
        fold_summary = summarize_scored_rows(scored_rows)
        folds.append(
            {
                "month": test_month,
                "train_rows": len(train_rows),
                "test_rows": len(test_rows),
                "evaluated_rows": len(scored_rows),
                **metadata,
                "metrics": fold_summary,
            }
        )
        if "all" in fold_summary:
            all_metrics = fold_summary["all"]
            print(
                f"{test_month}: old={all_metrics['old_draw_plus_elo_log_loss']:.4f} "
                f"candidate={all_metrics['candidate_winner_log_loss']:.4f} "
                f"delta={all_metrics['delta_candidate_minus_old']:.4f}",
                flush=True,
            )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": time.perf_counter() - started,
        "cache_path": str(args.cache_path),
        "participant_cache_path": str(args.participant_cache_path),
        "selected_months": candidate_months,
        "rows": {
            "loaded_valid": len(rows),
            "candidate_examples": len(all_candidate_examples),
            "evaluated": len(all_scored),
        },
        "folds": folds,
        "aggregate_metrics": summarize_scored_rows(all_scored),
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["aggregate_metrics"], indent=2), flush=True)
    print(f"Wrote report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
