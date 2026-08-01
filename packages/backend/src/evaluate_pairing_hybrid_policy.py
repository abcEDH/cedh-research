#!/usr/bin/env python3
"""Learn and evaluate a hybrid pairing policy from pairing evaluation JSON."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from summarize_pairing_evaluation import load_rows


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def split_tournaments(
    rows: list[dict[str, Any]],
    *,
    train_fraction: float,
    seed: int,
) -> tuple[set[str], set[str]]:
    by_bucket: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for row in rows:
        tournament_id = str(row["tournament_id"])
        if tournament_id in seen:
            continue
        seen.add(tournament_id)
        by_bucket[str(row["size_bucket"])].append(tournament_id)

    rng = random.Random(seed)
    train_ids: set[str] = set()
    test_ids: set[str] = set()
    for tournament_ids in by_bucket.values():
        shuffled = tournament_ids[:]
        rng.shuffle(shuffled)
        train_count = max(1, min(len(shuffled) - 1, round(len(shuffled) * train_fraction))) if len(shuffled) > 1 else len(shuffled)
        train_ids.update(shuffled[:train_count])
        test_ids.update(shuffled[train_count:])
    return train_ids, test_ids


def best_candidate(rows: list[dict[str, Any]], metric: str) -> str | None:
    by_candidate: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate"])].append(float(row[metric]))
    if not by_candidate:
        return None
    return max(
        by_candidate,
        key=lambda candidate: (
            statistics.fmean(by_candidate[candidate]),
            len(by_candidate[candidate]),
            candidate,
        ),
    )


def learn_policy(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    by_size_round: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    by_size: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_size_round[(str(row["size_bucket"]), int(row["round_number"]))].append(row)
        by_size[str(row["size_bucket"])].append(row)

    policy = {
        "by_size_round": {
            f"{size}:{round_number}": best_candidate(group_rows, metric)
            for (size, round_number), group_rows in sorted(by_size_round.items())
        },
        "by_size": {
            size: best_candidate(group_rows, metric)
            for size, group_rows in sorted(by_size.items())
        },
        "global": best_candidate(rows, metric),
    }
    return policy


def policy_candidate(policy: dict[str, Any], row: dict[str, Any]) -> str | None:
    size = str(row["size_bucket"])
    round_number = int(row["round_number"])
    return (
        policy["by_size_round"].get(f"{size}:{round_number}")
        or policy["by_size"].get(size)
        or policy.get("global")
    )


def evaluate_policy(rows: list[dict[str, Any]], policy: dict[str, Any], metric: str) -> dict[str, Any]:
    by_event_round: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_event_round[(str(row["tournament_id"]), int(row["round_number"]))][str(row["candidate"])] = row

    scored: list[float] = []
    misses = 0
    choices: dict[str, int] = defaultdict(int)
    for candidate_rows in by_event_round.values():
        sample_row = next(iter(candidate_rows.values()))
        candidate = policy_candidate(policy, sample_row)
        if candidate is None or candidate not in candidate_rows:
            misses += 1
            continue
        choices[candidate] += 1
        scored.append(float(candidate_rows[candidate][metric]))
    return {
        "event_rounds": len(by_event_round),
        "scored_event_rounds": len(scored),
        "misses": misses,
        metric: mean(scored),
        "choices": dict(sorted(choices.items())),
    }


def evaluate_single_candidates(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    by_candidate: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_candidate[str(row["candidate"])].append(float(row[metric]))
    return {
        candidate: {
            "event_rounds": len(values),
            metric: mean(values),
        }
        for candidate, values in sorted(by_candidate.items())
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--metric", default="pair_recall", choices=["pair_recall", "pair_recall_best", "exact_pod_recall"])
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    rows = load_rows(args.paths)
    train_ids, test_ids = split_tournaments(rows, train_fraction=args.train_fraction, seed=args.seed)
    train_rows = [row for row in rows if str(row["tournament_id"]) in train_ids]
    test_rows = [row for row in rows if str(row["tournament_id"]) in test_ids]
    policy = learn_policy(train_rows, args.metric)
    payload = {
        "config": {
            "metric": args.metric,
            "train_fraction": args.train_fraction,
            "seed": args.seed,
            "paths": [str(path) for path in args.paths],
        },
        "split": {
            "train_tournaments": sorted(train_ids),
            "test_tournaments": sorted(test_ids),
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
        },
        "policy": policy,
        "test": {
            "hybrid": evaluate_policy(test_rows, policy, args.metric),
            "single_candidates": evaluate_single_candidates(test_rows, args.metric),
        },
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
