#!/usr/bin/env python3
"""Canonical decisive-only Elo benchmark runner.

This script exists to keep one-off checks and grid scans on the exact same code
path. It benchmarks P(win | not drawn) using a cached ordered game list.

Rules:
- If any participant row in a pod is marked draw, treat the whole pod as draw.
- Draw pods update ratings but do not contribute to log loss.
- Decisive pods use seat-adjusted expectations.
- Draw pods optionally use seat-adjusted expectations via --draw-seat.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import pickle
from pathlib import Path
from typing import Any

DEFAULT_RATING = 1500.0
ELO_BASE = 2.0
ELO_DIVISOR = 200.0
DEFAULT_SEAT_ELO_BONUS = {
    0: 0.0,
    1: -52.0,
    2: -96.0,
    3: -145.0,
}


def parse_k_values(raw: str) -> list[int]:
    values = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        values.append(int(chunk))
    if not values:
        raise ValueError("expected at least one K value")
    return values


def load_ordered_games(cache_path: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    with cache_path.open("rb") as handle:
        payload = pickle.load(handle)
    if not isinstance(payload, dict) or "ordered_games" not in payload:
        raise ValueError(f"cache at {cache_path} does not contain ordered_games")
    ordered_games = payload["ordered_games"]
    if not isinstance(ordered_games, list):
        raise ValueError("ordered_games is not a list")
    return ordered_games


def is_draw_pod(rows: list[dict[str, Any]]) -> bool:
    return any((row.get("result") or "").lower() == "draw" for row in rows)


def winner_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["player_id"])
        for row in rows
        if (row.get("result") or "").lower() == "win"
    }


def is_valid_pod(rows: list[dict[str, Any]]) -> bool:
    """A valid pod has either any draw row or exactly one winner row."""
    if is_draw_pod(rows):
        return True
    return len(winner_ids(rows)) == 1


def rating_equities(
    ratings: list[float],
    seats: list[int | None],
    use_seat: bool,
    seat_bonus: dict[int, float],
    seat_scale: float = 1.0,
) -> list[float]:
    equities: list[float] = []
    for index, rating in enumerate(ratings):
        effective = rating
        if use_seat:
            seat = seats[index]
            if seat in seat_bonus:
                effective += seat_bonus[seat] * seat_scale
        equities.append(pow(ELO_BASE, effective / ELO_DIVISOR))
    return equities


def expected_scores(
    ratings: list[float],
    seats: list[int | None],
    use_seat: bool,
    seat_bonus: dict[int, float],
    seat_scale: float = 1.0,
) -> list[float]:
    equities = rating_equities(ratings, seats, use_seat, seat_bonus, seat_scale)
    total = sum(equities)
    return [equity / total for equity in equities]


def evaluate_config(
    ordered_games: list[tuple[str, list[dict[str, Any]]]],
    player_decisive_k: int,
    player_draw_k: int,
    draw_seat: bool,
    seat_bonus: dict[int, float] | None = None,
    draw_seat_scale: float = 1.0,
) -> dict[str, Any]:
    seat_bonus = seat_bonus or DEFAULT_SEAT_ELO_BONUS
    ratings: dict[str, float] = {}
    log_losses: list[float] = []
    brier_sum = 0.0
    brier_count = 0
    decisive_games = 0
    winner_hits = 0

    for _game_id, rows in ordered_games:
        if not is_valid_pod(rows):
            continue
        player_ids = [str(row["player_id"]) for row in rows]
        current_ratings = [ratings.get(player_id, DEFAULT_RATING) for player_id in player_ids]
        seats = [row.get("seat_position") for row in rows]
        draw_pod = is_draw_pod(rows)

        if draw_pod:
            actual_scores = [1.0 / len(player_ids)] * len(player_ids)
            expected = expected_scores(
                current_ratings,
                seats,
                use_seat=draw_seat,
                seat_bonus=seat_bonus,
                seat_scale=draw_seat_scale,
            )
            k_factor = player_draw_k
        else:
            decisive_games += 1
            winners = winner_ids(rows)
            expected = expected_scores(
                current_ratings,
                seats,
                use_seat=True,
                seat_bonus=seat_bonus,
            )
            k_factor = player_decisive_k
            actual_scores = [
                1.0 if (row.get("result") or "").lower() == "win" else 0.0
                for row in rows
            ]

            if winners:
                predicted_index = max(range(len(expected)), key=lambda idx: expected[idx])
                if player_ids[predicted_index] in winners:
                    winner_hits += 1
                winner_probability = sum(
                    expected[index]
                    for index, player_id in enumerate(player_ids)
                    if player_id in winners
                )
                winner_probability = min(max(winner_probability, 1e-15), 1.0)
                log_losses.append(-math.log(winner_probability))

            targets = [1.0 if player_id in winners else 0.0 for player_id in player_ids]
            brier_sum += sum(
                (expected[index] - targets[index]) ** 2 for index in range(len(expected))
            ) / len(expected)
            brier_count += 1

        for index, player_id in enumerate(player_ids):
            ratings[player_id] = current_ratings[index] + k_factor * (
                actual_scores[index] - expected[index]
            )

    return {
        "player_decisive_k": player_decisive_k,
        "player_draw_k": player_draw_k,
        "draw_seat": draw_seat,
        "log_loss": sum(log_losses) / len(log_losses),
        "brier": brier_sum / brier_count if brier_count else None,
        "winner_hit_rate": winner_hits / decisive_games if decisive_games else None,
        "scored_games": len(log_losses),
        "decisive_games": decisive_games,
    }


def run_grid(
    ordered_games: list[tuple[str, list[dict[str, Any]]]],
    player_decisive_ks: list[int],
    player_draw_ks: list[int],
    draw_seat_values: list[bool],
    seat_bonus: dict[int, float] | None = None,
    draw_seat_scale: float = 1.0,
) -> dict[str, Any]:
    results = []
    best: dict[str, Any] | None = None
    total = len(player_decisive_ks) * len(player_draw_ks) * len(draw_seat_values)

    for index, (draw_seat, decisive_k, draw_k) in enumerate(
        itertools.product(draw_seat_values, player_decisive_ks, player_draw_ks),
        start=1,
    ):
        print(
            f"variant {index}/{total}: draw_seat={draw_seat} "
            f"pdk={decisive_k} pdrk={draw_k}",
            flush=True,
        )
        result = evaluate_config(
            ordered_games,
            player_decisive_k=decisive_k,
            player_draw_k=draw_k,
            draw_seat=draw_seat,
            seat_bonus=seat_bonus,
            draw_seat_scale=draw_seat_scale,
        )
        results.append(result)
        if best is None or result["log_loss"] < best["log_loss"]:
            best = result
        print(
            "current best: "
            f"draw_seat={best['draw_seat']} "
            f"pdk={best['player_decisive_k']} "
            f"pdrk={best['player_draw_k']} "
            f"ll={best['log_loss']:.6f}",
            flush=True,
        )

    return {
        "variant_count": len(results),
        "best": best,
        "top20": sorted(results, key=lambda item: item["log_loss"])[:20],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical decisive-only Elo benchmark")
    parser.add_argument(
        "--cache",
        default="/tmp/elo_scan_input_all_history.pkl",
        help="Path to cached ordered games pickle",
    )
    parser.add_argument("--player-decisive-k", type=int, help="Single-config decisive K")
    parser.add_argument("--player-draw-k", type=int, help="Single-config draw K")
    parser.add_argument(
        "--draw-seat",
        choices=("on", "off"),
        help="Single-config draw seat flag",
    )
    parser.add_argument(
        "--player-decisive-ks",
        help="Comma-separated decisive K values for grid mode",
    )
    parser.add_argument(
        "--player-draw-ks",
        help="Comma-separated draw K values for grid mode",
    )
    parser.add_argument(
        "--draw-seat-options",
        default="off,on",
        help="Comma-separated draw seat options for grid mode: off,on",
    )
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument("--seat2", type=float, default=DEFAULT_SEAT_ELO_BONUS[1])
    parser.add_argument("--seat3", type=float, default=DEFAULT_SEAT_ELO_BONUS[2])
    parser.add_argument("--seat4", type=float, default=DEFAULT_SEAT_ELO_BONUS[3])
    parser.add_argument("--draw-seat-scale", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ordered_games = load_ordered_games(Path(args.cache))
    print(f"loaded {len(ordered_games):,} games from cache", flush=True)
    seat_bonus = {0: 0.0, 1: args.seat2, 2: args.seat3, 3: args.seat4}

    single_mode = (
        args.player_decisive_k is not None
        and args.player_draw_k is not None
        and args.draw_seat is not None
    )
    grid_mode = args.player_decisive_ks and args.player_draw_ks
    if single_mode == bool(grid_mode):
        raise SystemExit(
            "Provide either single-config args "
            "(--player-decisive-k/--player-draw-k/--draw-seat) "
            "or grid args (--player-decisive-ks/--player-draw-ks)"
        )

    if single_mode:
        result = evaluate_config(
            ordered_games,
            player_decisive_k=args.player_decisive_k,
            player_draw_k=args.player_draw_k,
            draw_seat=args.draw_seat == "on",
            seat_bonus=seat_bonus,
            draw_seat_scale=args.draw_seat_scale,
        )
        payload: dict[str, Any] = result
    else:
        decisive_ks = parse_k_values(args.player_decisive_ks)
        draw_ks = parse_k_values(args.player_draw_ks)
        draw_seat_values = []
        for raw in args.draw_seat_options.split(","):
            normalized = raw.strip().lower()
            if normalized == "on":
                draw_seat_values.append(True)
            elif normalized == "off":
                draw_seat_values.append(False)
            elif normalized:
                raise ValueError(f"unknown draw seat option: {raw}")
        if not draw_seat_values:
            raise ValueError("expected at least one draw seat option")
        payload = run_grid(
            ordered_games,
            decisive_ks,
            draw_ks,
            draw_seat_values,
            seat_bonus=seat_bonus,
            draw_seat_scale=args.draw_seat_scale,
        )

    print(json.dumps(payload, indent=2), flush=True)
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2))
        print(f"wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
