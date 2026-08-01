#!/usr/bin/env python3
"""Summarize pairing evaluation JSON by event size and Swiss round."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def size_bucket(player_count: int) -> str:
    if player_count < 40:
        return "small"
    if player_count < 96:
        return "medium"
    return "large"


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for result in payload.get("results") or []:
            tournament = result.get("tournament") or {}
            player_count = int(tournament.get("player_count") or 0)
            for row in result.get("rounds") or []:
                metrics = row.get("metrics") or {}
                rows.append(
                    {
                        "source": str(path),
                        "tournament_id": tournament.get("id"),
                        "tournament_name": tournament.get("name"),
                        "player_count": player_count,
                        "size_bucket": size_bucket(player_count),
                        "round_number": int(row.get("round_number") or 0),
                        "candidate": row.get("candidate"),
                        "pair_recall": float(metrics.get("pair_recall") or 0.0),
                        "pair_recall_best": float(metrics.get("pair_recall_best") or 0.0),
                        "exact_pod_recall": float(metrics.get("exact_pod_recall") or 0.0),
                    }
                )
    return rows


def rank_groups(rows: list[dict[str, Any]], group_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[tuple(row[key] for key in group_keys)][str(row["candidate"])].append(row)

    summaries: list[dict[str, Any]] = []
    for group, by_candidate in sorted(grouped.items()):
        rankings = []
        for candidate, candidate_rows in by_candidate.items():
            rankings.append(
                {
                    "candidate": candidate,
                    "rounds": len(candidate_rows),
                    "pair_recall": mean([row["pair_recall"] for row in candidate_rows]),
                    "pair_recall_best": mean([row["pair_recall_best"] for row in candidate_rows]),
                    "exact_pod_recall": mean([row["exact_pod_recall"] for row in candidate_rows]),
                }
            )
        rankings.sort(key=lambda row: (row["pair_recall"], row["pair_recall_best"]), reverse=True)
        summaries.append(
            {
                "group": dict(zip(group_keys, group, strict=True)),
                "rankings": rankings,
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="Emit full JSON instead of a text summary.")
    args = parser.parse_args()

    rows = load_rows(args.paths)
    payload = {
        "overall": rank_groups(rows, tuple()),
        "by_size": rank_groups(rows, ("size_bucket",)),
        "by_size_round": rank_groups(rows, ("size_bucket", "round_number")),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return

    for section in ("by_size", "by_size_round"):
        print(f"== {section} ==")
        for group in payload[section]:
            label = ", ".join(f"{key}={value}" for key, value in group["group"].items()) or "all"
            print(label)
            for row in group["rankings"][: args.top]:
                print(
                    f"  {row['candidate']:36s} "
                    f"pair={row['pair_recall']:.3f} "
                    f"best={row['pair_recall_best']:.3f} "
                    f"exact={row['exact_pod_recall']:.3f}"
                )


if __name__ == "__main__":
    main()
