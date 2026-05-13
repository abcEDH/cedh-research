#!/usr/bin/env python3
"""Summarize tournament backtest results by rounds remaining and size bucket."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def load_json_with_log_prefix(path: Path) -> dict[str, Any]:
    text = path.read_text()
    start = text.find("{")
    if start < 0:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(text[start:])


def rounds_remaining_bucket(rounds_remaining: int) -> str:
    if rounds_remaining <= 1:
        return "1"
    if rounds_remaining == 2:
        return "2"
    if 3 <= rounds_remaining <= 4:
        return "3-4"
    return "5+"


def tournament_size_bucket(player_count: int) -> str:
    if player_count < 64:
        return "<64"
    if player_count < 128:
        return "64-127"
    if player_count < 256:
        return "128-255"
    return "256+"


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not cases:
        return {"cases": 0}
    metric_names = [
        "actual_winner_probability",
        "winner_log_loss",
        "top_cut_brier",
        "top_cut_overlap",
        "round_draw_rate_mae",
    ]
    averages: dict[str, float] = {}
    for metric_name in metric_names:
        values = [float(case["metrics"][metric_name]) for case in cases if case["metrics"].get(metric_name) is not None]
        if values:
            averages[metric_name] = mean(values)
    return {"cases": len(cases), "average_metrics": averages}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Backtest JSON path")
    parser.add_argument("--output", help="Optional output path")
    args = parser.parse_args()

    payload = load_json_with_log_prefix(Path(args.input))
    cases = [row for row in payload.get("results", []) if "metrics" in row and "checkpoint" in row and "tournament" in row]

    by_rounds_remaining: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_size_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_rounds_and_size: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for case in cases:
        rounds_bucket = rounds_remaining_bucket(int(case["checkpoint"]["remaining_rounds"]))
        size_bucket = tournament_size_bucket(int(case["tournament"]["player_count"]))
        by_rounds_remaining[rounds_bucket].append(case)
        by_size_bucket[size_bucket].append(case)
        by_rounds_and_size[(rounds_bucket, size_bucket)].append(case)

    report = {
        "source": args.input,
        "overall": summarize_cases(cases),
        "by_rounds_remaining": {
            bucket: summarize_cases(bucket_cases)
            for bucket, bucket_cases in sorted(
                by_rounds_remaining.items(),
                key=lambda item: ["1", "2", "3-4", "5+"].index(item[0]),
            )
        },
        "by_tournament_size": {
            bucket: summarize_cases(bucket_cases)
            for bucket, bucket_cases in sorted(
                by_size_bucket.items(),
                key=lambda item: ["<64", "64-127", "128-255", "256+"].index(item[0]),
            )
        },
        "by_rounds_remaining_and_size": {
            f"{rounds_bucket} | {size_bucket}": summarize_cases(bucket_cases)
            for (rounds_bucket, size_bucket), bucket_cases in sorted(
                by_rounds_and_size.items(),
                key=lambda item: (
                    ["1", "2", "3-4", "5+"].index(item[0][0]),
                    ["<64", "64-127", "128-255", "256+"].index(item[0][1]),
                ),
            )
        },
    }

    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered)


if __name__ == "__main__":
    main()
