"""Versioned internal prediction model; displayed TopDeck Elo is independent."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

MODEL_VERSION = "2026-09-18-quarterly-v1"
ELO_BASE = 2.0
ELO_DIVISOR = 200.0
SWISS_WIN_K = 64.20106085407248
SWISS_DRAW_K = 21.14298097296857
TOPCUT_WIN_K = 39.67175522623664
LEAGUE_MULTIPLIER = 0.5794326409119744
SWISS_SEAT_OFFSETS = dict(enumerate((0.0, -48.820457256958306, -97.04491395828074, -144.80626927577129), 1))
TOPCUT_SEAT_OFFSETS = dict(enumerate((0.0, -117.5921368942531, -172.63550764675733, -227.7663864826161), 1))


def is_top_cut(round_name: str | None, round_number: int | None = None) -> bool:
    return round_number is None and bool(re.search(r"top\s*\d+|final", round_name or "", re.I))


def stage_size(round_name: str | None) -> int | None:
    label = (round_name or "").lower()
    match = re.search(r"top\s*(\d+)", label)
    if match:
        return int(match.group(1))
    return 8 if "semi" in label else 4 if "final" in label else None


def seat_offsets(top_cut: bool = False) -> dict[int, float]:
    return TOPCUT_SEAT_OFFSETS if top_cut else SWISS_SEAT_OFFSETS


def learning_rate(*, top_cut: bool = False, draw: bool = False, league: bool = False) -> float:
    if top_cut and draw:
        raise ValueError("Resolve top-cut draw advancement before Elo updates")
    k = TOPCUT_WIN_K if top_cut else SWISS_DRAW_K if draw else SWISS_WIN_K
    return k * (LEAGUE_MULTIPLIER if league else 1.0)


def resolve_topcut_draws(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return modeled win/loss copies; never mutate source results.

    A sole player present in the next smaller recorded stage wins. Otherwise
    seat 1 wins. Ambiguous advancement or missing seat 1 fails closed.
    Call on the entire eligible event history, including its later stages.
    """
    stages: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    games: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        if not is_top_cut(row.get("round_name"), row.get("round_number")):
            continue
        games[row["game_id"]].append(row)
        size = stage_size(row.get("round_name"))
        if size is not None:
            stages[row["tournament_id"]][size].add(row["player_id"])
    winners = {}
    for gid, rows in games.items():
        if not any(r.get("result") == "draw" for r in rows):
            continue
        if any(r.get("result") == "win" for r in rows):
            raise ValueError(f"Mixed win/draw top-cut outcomes: {gid}")
        size = stage_size(rows[0].get("round_name"))
        event_stages = stages[rows[0]["tournament_id"]]
        later = [s for s in event_stages if size is not None and s < size]
        advancing = set()
        if later:
            advancing = {r["player_id"] for r in rows} & event_stages[max(later)]
            if len(advancing) > 1:
                raise ValueError(f"Multiple advancing players for top-cut draw: {gid}")
        if len(advancing) == 1:
            winners[gid] = advancing.pop()
        else:
            first = {r["player_id"] for r in rows if r.get("seat_position") == 0}
            if len(first) != 1:
                raise ValueError(f"Cannot identify seat 1 for top-cut draw: {gid}")
            winners[gid] = first.pop()
    return [
        dict(row, result="win" if row["player_id"] == winners[row["game_id"]] else "loss", is_draw=False)
        if row["game_id"] in winners
        else row
        for row in results
    ]


def rating_equity(rating: float) -> float:
    return pow(ELO_BASE, rating / ELO_DIVISOR)


def parameter_fingerprint() -> str:
    """Invalidate derived simulation state on value changes, even without a version bump."""
    payload = {
        "model_version": MODEL_VERSION,
        "base": ELO_BASE,
        "divisor": ELO_DIVISOR,
        "league_multiplier": LEAGUE_MULTIPLIER,
        "swiss_win_k": SWISS_WIN_K,
        "swiss_draw_k": SWISS_DRAW_K,
        "topcut_win_k": TOPCUT_WIN_K,
        "swiss_seats": SWISS_SEAT_OFFSETS,
        "topcut_seats": TOPCUT_SEAT_OFFSETS,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
