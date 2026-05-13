#!/usr/bin/env python3
"""Train and tune the pod-level P(draw) model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import re
from bisect import bisect_left
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from dateutil import parser as date_parser
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from ingest import SupabaseClient, load_local_env

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_CACHE_PATH = DATA_DIR / "draw_model_rich_cache.pkl"
DEFAULT_ARTIFACT_PATH = DATA_DIR / "draw_model_artifact.pkl"
DEFAULT_REPORT_PATH = DATA_DIR / "draw_model_report.json"

RESULTS_SELECT = (
    "game_id,tournament_id,start_date,round_number,round_name,table_number,"
    "player_id,entry_id,result"
)
EVENTS_SELECT = "game_id,player_id,rating_before"
SEATS_SELECT = "game_id,entry_id,seat_position"
TOURNAMENTS_SELECT = "id,start_date,player_count,name,topdeck_tid,top_cut,state,country"


def parse_datetime_value(value: Any) -> datetime:
    return date_parser.parse(str(value))


@dataclass(slots=True)
class DrawPodRow:
    game_id: str
    date: datetime
    is_draw: int
    is_swiss: int
    pod_size: int
    spread: float
    mean_elo: float
    median_elo: float
    top2_mean_elo: float
    top3_mean_elo: float
    top1_minus_top2: float
    elo_std: float
    elo_gini: float
    high1550: int
    high1600: int
    high1650: int
    high1700: int
    high1800: int
    seat_highest: int
    seat_second: int
    top2_adjacent: int
    swiss_progress: float
    round_number: int
    rounds_remaining: int
    cut_fraction: float
    cut_size_bucket: int
    current_cut_line_points: float
    expected_cut_line_points: float
    avg_estimated_omw: float
    min_estimated_omw: float
    max_estimated_omw: float
    omw_std_within_pod: float
    avg_same_points_omw_percentile: float
    min_same_points_omw_percentile: float
    max_same_points_omw_percentile: float
    count_bottom_quartile_omw_in_same_points_group: int
    count_currently_in_cut: int
    count_currently_outside_cut: int
    count_players_currently_safe: int
    count_players_currently_dead: int
    all_players_live: int
    count_draw_secures_cut: int
    count_win_secures_cut: int
    count_must_win_to_stay_live: int
    all_players_draw_secures_cut: int
    mixed_pod_cut_incentives: int
    some_locked_some_must_win: int
    avg_rank_minus_cut: float
    min_rank_minus_cut: float
    rank_spread_within_pod: int
    avg_draw_secure_rank_delta: float
    avg_win_secure_rank_delta: float
    avg_points_percentile: float
    max_points_percentile: float
    points_std: float
    avg_cut_margin: float
    min_abs_cut_margin: float
    avg_points_to_current_cut: float
    min_points_to_current_cut: float
    avg_points_to_cut: float
    min_points_to_cut: float
    count_above_cut_line: int
    count_near_cut_line: int
    count_locked_for_current_cut: int
    count_dead_for_current_cut: int
    count_draw_safe_for_current_cut: int
    count_must_win_for_current_cut: int
    all_players_draw_safe_for_current_cut: int
    count_locked_for_cut: int
    count_dead_for_cut: int
    count_live_for_cut: int
    count_draw_safe_for_cut: int
    count_must_win_for_cut: int
    all_players_draw_safe: int
    is_last_swiss_round: int
    is_penultimate_swiss_round: int
    month: int
    quarter: int
    tournament_size: int
    size_bucket: int
    global_recent_draw_rate_90d: float
    avg_player_prior_draw: float
    median_player_prior_draw: float
    min_player_prior_draw: float
    max_player_prior_draw: float
    prior_draw_std: float
    prior_draw_range: float
    count_high_draw_players: int
    count_high_win_low_draw_players: int
    draw_rate_range_above_threshold: int
    avg_player_prior_win: float
    max_player_prior_win: float
    avg_player_prior_decisive: float
    max_player_prior_decisive: float
    prior_pair_meetings_avg: float
    prior_pair_meetings_max: int
    global_pair_meetings_avg: float
    global_pair_meetings_max: int
    series_prior_draw_rate: float
    series_events_seen: int
    state_prior_draw_rate: float
    country_prior_draw_rate: float
    count_players_near_cut_band: int
    tournament_id: str = ""
    tournament_name: str = ""
    series_key: str = ""
    round_name: str = ""
    table_number: int = -1
    series_prior_draw_rate_smoothed_50: float = 0.0
    series_prior_draw_rate_smoothed_100: float = 0.0
    series_prior_draw_rate_smoothed_250: float = 0.0
    series_prior_draw_rate_smoothed_500: float = 0.0
    series_events_seen_log: float = 0.0
    avg_player_prior_draw_smoothed_50: float = 0.0
    median_player_prior_draw_smoothed_50: float = 0.0
    max_player_prior_draw_smoothed_50: float = 0.0
    avg_player_prior_games: float = 0.0
    min_player_prior_games: float = 0.0
    player_prior_confidence_avg: float = 0.0
    all_players_can_draw_into_cut: int = 0
    any_player_eliminated_by_draw: int = 0
    all_players_locked_with_draw: int = 0
    count_players_draw_as_good_as_win: int = 0
    count_players_loss_eliminates: int = 0
    draw_preserves_cut_rank_count: int = 0
    win_changes_cut_status_count: int = 0
    same_points_count_in_pod: int = 0
    all_players_same_points: int = 0
    points_range_within_pod: int = 0
    min_points_in_pod: int = 0
    max_points_in_pod: int = 0
    all_players_above_projected_cut_line: int = 0
    all_players_within_one_point_of_cut_line: int = 0
    last_round_cut_fraction: float = 0.0
    penultimate_round_cut_fraction: float = 0.0
    round_number_size_bucket: float = 0.0
    last_round_size_bucket: int = 0
    round_size_cut_bucket_key: int = 0
    round_size_cut_prior_draw_rate_smoothed_100: float = 0.0
    decisive_win_probability_entropy: float = 0.0
    max_decisive_win_probability: float = 0.0
    min_decisive_win_probability: float = 0.0
    decisive_win_probability_spread: float = 0.0
    any_repeat_pair: int = 0
    count_repeat_pairs: int = 0
    pod_size_round_number: float = 0.0
    pod_size_is_last_swiss_round: int = 0
    pod_size_cut_fraction: float = 0.0
    pod_size_series_prior_draw_rate: float = 0.0
    series_pod_size_prior_draw_rate_smoothed_100: float = 0.0
    series_swiss_prior_draw_rate_smoothed_100: float = 0.0
    series_prior_draw_rate_residual: float = 0.0
    count_players_with_no_history: int = 0
    count_players_with_low_history: int = 0
    all_elos_default: int = 0
    count_default_elos: int = 0
    seat_data_missing: int = 0
    min_draw_secure_rank: int = 0
    max_draw_secure_rank: int = 0
    draw_secure_rank_spread: int = 0
    all_players_draw_rank_within_cut_plus_4: int = 0
    all_players_draw_rank_within_cut_plus_8: int = 0
    bye_fraction: float = 0.0
    bye_line_points: float = 0.0
    expected_bye_line_points: float = 0.0
    count_currently_in_bye: int = 0
    count_draw_secures_bye: int = 0
    count_win_secures_bye: int = 0
    count_must_win_for_bye: int = 0
    count_players_win_only_live: int = 0
    count_players_win_only_live_for_bye: int = 0
    all_players_draw_lock_cut: int = 0
    all_players_draw_lock_bye: int = 0
    min_draw_rank_margin_to_cut: float = 0.0
    min_draw_rank_margin_to_bye: float = 0.0
    count_players_draw_makes_cut: int = 0
    count_players_draw_makes_bye: int = 0
    draw_hurts_any_player_cut_status: int = 0
    draw_hurts_any_player_bye_status: int = 0
    draw_hurts_any_player_status: int = 0
    all_players_above_cut_after_draw: int = 0
    all_players_above_bye_after_draw: int = 0
    all_players_above_cut_after_loss: int = 0
    all_players_above_bye_after_loss: int = 0
    pod_has_asymmetric_cut_incentive: int = 0
    pod_has_asymmetric_bye_incentive: int = 0
    pod_has_asymmetric_incentive: int = 0
    draw_vs_win_status_same_count: int = 0
    pairwise_mutual_draw_benefit_count: int = 0
    count_players_draw_as_good_as_win_for_bye: int = 0


@dataclass(slots=True)
class ModelSelection:
    feature_set_name: str
    features: list[str]
    half_life: int
    learning_rate: float
    max_leaf_nodes: int
    min_samples_leaf: int
    max_depth: int | None
    l2_regularization: float


def normalize_series_key(name: str | None) -> str:
    if not name:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()
    normalized = re.sub(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        " ",
        normalized,
    )
    normalized = re.sub(r"\b20\d{2}\b", " ", normalized)
    normalized = re.sub(r"\b\d{1,2}(st|nd|rd|th)?\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or "unknown_series"


def smoothed_rate(successes: float, total: float, fallback_rate: float, prior_weight: float) -> float:
    if prior_weight <= 0:
        return (successes / total) if total else fallback_rate
    return (successes + (fallback_rate * prior_weight)) / (total + prior_weight)


def decisive_probability_features(ratings: list[float]) -> tuple[float, float, float, float]:
    if not ratings:
        return (0.0, 0.0, 0.0, 0.0)
    equities = np.asarray([10.0 ** (rating / 400.0) for rating in ratings], dtype=float)
    total = float(equities.sum()) or 1.0
    probabilities = equities / total
    entropy = -float(np.sum(probabilities * np.log(np.clip(probabilities, 1e-12, 1.0))))
    normalized_entropy = entropy / float(np.log(len(probabilities))) if len(probabilities) > 1 else 0.0
    max_probability = float(probabilities.max())
    min_probability = float(probabilities.min())
    return (
        normalized_entropy,
        max_probability,
        min_probability,
        max_probability - min_probability,
    )


def gini(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(float(value) for value in values)
    total = sum(sorted_values)
    if total <= 0:
        return 0.0
    n = len(sorted_values)
    cumulative = sum((2 * index - n - 1) * value for index, value in enumerate(sorted_values, start=1))
    return cumulative / (n * total)


def hypothetical_rank_by_player(
    player_ids: list[str],
    *,
    target_player_ids: list[str] | None = None,
    points_by_player: dict[str, int],
    estimated_omw_by_player: dict[str, float],
    tiebreak_seed_by_player: dict[str, int],
    point_delta: int,
) -> dict[str, int]:
    fallback_seed = len(player_ids) + 1_000_000
    target_ids = target_player_ids if target_player_ids is not None else player_ids
    sort_keys = sorted(
        (
            -points_by_player.get(player_id, 0),
            -estimated_omw_by_player.get(player_id, 0.0),
            tiebreak_seed_by_player.get(player_id, fallback_seed),
            player_id,
        )
        for player_id in player_ids
    )

    ranks: dict[str, int] = {}
    for player_id in target_ids:
        target_key = (
            -(points_by_player.get(player_id, 0) + point_delta),
            -estimated_omw_by_player.get(player_id, 0.0),
            tiebreak_seed_by_player.get(player_id, fallback_seed),
            player_id,
        )
        ranks[player_id] = bisect_left(sort_keys, target_key) + 1
    return ranks


def topdeck_bye_rank(cut_size: int) -> int | None:
    if cut_size == 40:
        return 8
    if cut_size == 10:
        return 2
    return None


def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    *,
    limit: int = 1000,
    label: str | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    started = datetime.now()
    while True:
        page = client.select(
            table,
            {**params, "limit": str(limit), "offset": str(offset)},
            max_retries=8,
        )
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        if offset % 25_000 == 0:
            elapsed = (datetime.now() - started).total_seconds()
            print(f"Fetched {offset:,} rows from {label or table} in {elapsed:.1f}s", flush=True)
    return rows


def load_pods(cache_path: Path) -> list[DrawPodRow] | None:
    if not cache_path.exists():
        return None
    with cache_path.open("rb") as handle:
        raw_rows = pickle.load(handle)
    return [DrawPodRow(**row) if isinstance(row, dict) else row for row in raw_rows]


def save_pods(cache_path: Path, pods: list[DrawPodRow]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as handle:
        pickle.dump([asdict(pod) for pod in pods], handle)


def load_raw_rows(cache_path: Path) -> list[dict[str, Any]] | None:
    if not cache_path.exists():
        return None
    with cache_path.open("rb") as handle:
        return pickle.load(handle)


def save_raw_rows(cache_path: Path, rows: list[dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as handle:
        pickle.dump(rows, handle)


def fetch_or_load_raw_rows(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    *,
    label: str,
    raw_data_cache_dir: Path | None,
) -> list[dict[str, Any]]:
    cache_path = raw_data_cache_dir / f"{label}.pkl" if raw_data_cache_dir else None
    if cache_path:
        cached_rows = load_raw_rows(cache_path)
        if cached_rows is not None:
            print(f"Loaded raw {label}: {len(cached_rows):,} rows", flush=True)
            return cached_rows
    rows = fetch_all(client, table, params, label=label)
    if cache_path:
        save_raw_rows(cache_path, rows)
        print(f"Cached raw {label}: {len(rows):,} rows", flush=True)
    return rows


def build_rich_pod_cache(client: SupabaseClient, *, raw_data_cache_dir: Path | None = None) -> list[DrawPodRow]:
    print("Fetching game results...", flush=True)
    results = fetch_or_load_raw_rows(
        client,
        "global_elo_game_results",
        {
            "select": RESULTS_SELECT,
            "result": "neq.bye",
            "order": "start_date.asc,game_id.asc",
        },
        raw_data_cache_dir=raw_data_cache_dir,
        label="global_elo_game_results",
    )
    print(f"Fetched {len(results):,} result rows", flush=True)

    print("Fetching game events...", flush=True)
    events = fetch_or_load_raw_rows(
        client,
        "global_elo_game_events",
        {
            "select": EVENTS_SELECT,
            "region_type": "eq.global",
            "region_key": "eq.ALL",
        },
        raw_data_cache_dir=raw_data_cache_dir,
        label="global_elo_game_events",
    )
    rating_before = {
        (row["game_id"], row["player_id"]): float(row["rating_before"])
        for row in events
        if row.get("game_id") and row.get("player_id") and row.get("rating_before") is not None
    }

    print("Fetching seats...", flush=True)
    seats = fetch_or_load_raw_rows(
        client,
        "game_participants",
        {"select": SEATS_SELECT},
        raw_data_cache_dir=raw_data_cache_dir,
        label="game_participants",
    )
    seat_by_pair = {
        (row["game_id"], row["entry_id"]): int(row["seat_position"])
        for row in seats
        if row.get("game_id") and row.get("entry_id") and row.get("seat_position") is not None
    }

    print("Fetching tournaments...", flush=True)
    tournaments = fetch_or_load_raw_rows(
        client,
        "tournaments",
        {"select": TOURNAMENTS_SELECT},
        raw_data_cache_dir=raw_data_cache_dir,
        label="tournaments",
    )
    tournament_meta = {row["id"]: row for row in tournaments if row.get("id")}
    tournament_player_ids: dict[str, set[str]] = defaultdict(set)
    tournament_cut_sizes: dict[str, int] = {}
    tournament_series_keys: dict[str, str] = {}
    tournament_state_keys: dict[str, str] = {}
    tournament_country_keys: dict[str, str] = {}
    for row in results:
        tournament_id = str(row.get("tournament_id") or "")
        player_id = row.get("player_id")
        if tournament_id and player_id:
            tournament_player_ids[tournament_id].add(player_id)
    for tournament_id, meta in tournament_meta.items():
        top_cut_raw = meta.get("top_cut", 0)
        try:
            top_cut = int(top_cut_raw) if top_cut_raw is not None else 0
        except (TypeError, ValueError):
            top_cut = 0
        tournament_cut_sizes[str(tournament_id)] = max(0, top_cut)
        tournament_series_keys[str(tournament_id)] = normalize_series_key(meta.get("name"))
        tournament_state_keys[str(tournament_id)] = str(meta.get("state") or "").strip().lower()
        tournament_country_keys[str(tournament_id)] = str(meta.get("country") or "").strip().lower()

    by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    swiss_rounds_by_tournament: dict[str, set[int]] = defaultdict(set)
    for row in results:
        game_id = row.get("game_id")
        if game_id:
            by_game[game_id].append(row)
        tournament_id = row.get("tournament_id")
        round_number = row.get("round_number")
        if tournament_id and round_number is not None:
            try:
                swiss_rounds_by_tournament[tournament_id].add(int(round_number))
            except (TypeError, ValueError):
                # Ignore rows where round_number is missing or malformed in source data.
                continue
    max_swiss_round = {
        tournament_id: max(rounds)
        for tournament_id, rounds in swiss_rounds_by_tournament.items()
        if rounds
    }

    player_history: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    recent_draw_window: deque[tuple[datetime, int]] = deque()
    recent_draw_sum = 0
    pods: list[DrawPodRow] = []
    tournament_points: dict[str, dict[str, int]] = defaultdict(dict)
    pending_round_updates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    tournament_pair_meetings: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    tournament_opponents: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    global_pair_meetings: dict[tuple[str, str], int] = defaultdict(int)
    pending_round_pair_updates: dict[str, list[tuple[str, str]]] = defaultdict(list)
    last_round_key_by_tournament: dict[str, tuple[int, int, str, int]] = {}
    series_history: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    state_history: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    country_history: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    round_size_cut_history: dict[tuple[int, int, int], list[int]] = defaultdict(lambda: [0, 0])
    series_pod_size_history: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])
    series_swiss_history: dict[tuple[str, int], list[int]] = defaultdict(lambda: [0, 0])

    def parse_int(value: Any, default: int = -1) -> int:
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def bracket_round_sort_value(round_name: str | None) -> int:
        if not round_name:
            return 10_000
        lowered = round_name.strip().lower()
        if lowered == "finals":
            return 1_000_000
        if lowered == "semifinals":
            return 999_999
        if lowered.startswith("top "):
            suffix = lowered[4:].strip()
            try:
                return parse_int(suffix, 10_000)
            except ValueError:
                return 10_000
        return 10_000

    def round_key_for_rows(rows: list[dict[str, Any]]) -> tuple[int, int, str, int]:
        first = rows[0]
        round_number = parse_int(first.get("round_number"))
        if round_number >= 0:
            return (0, round_number, "", parse_int(first.get("table_number"), 10_000))
        round_name = str(first.get("round_name") or "")
        return (1, bracket_round_sort_value(round_name), round_name, parse_int(first.get("table_number"), 10_000))

    def score_delta(result: str | None) -> int:
        normalized = str(result or "").lower()
        if normalized == "win":
            return 5
        if normalized == "draw":
            return 1
        return 0

    def apply_pending_round_updates(tournament_id: str) -> None:
        if not pending_round_updates[tournament_id]:
            return
        tournament_state = tournament_points[tournament_id]
        for player_id, delta in pending_round_updates[tournament_id].items():
            tournament_state[player_id] = tournament_state.get(player_id, 0) + delta
        pending_round_updates[tournament_id].clear()
        if pending_round_pair_updates[tournament_id]:
            pair_counts = tournament_pair_meetings[tournament_id]
            opponent_sets = tournament_opponents[tournament_id]
            for pair in pending_round_pair_updates[tournament_id]:
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                global_pair_meetings[pair] += 1
                left, right = pair
                opponent_sets[left].add(right)
                opponent_sets[right].add(left)
            pending_round_pair_updates[tournament_id].clear()

    def game_sort_key(item: tuple[str, list[dict[str, Any]]]) -> tuple[str, str, tuple[int, int, str, int], int, str]:
        game_id, rows = item
        first = rows[0]
        return (
            str(first.get("start_date") or ""),
            str(first.get("tournament_id") or ""),
            round_key_for_rows(rows),
            parse_int(first.get("table_number"), 10_000),
            game_id,
        )

    for game_id, rows in sorted(by_game.items(), key=game_sort_key):
        ratings: list[float] = []
        player_ids: list[str] = []
        seat_positions: list[int | None] = []
        valid = True
        for row in rows:
            player_id = row.get("player_id")
            if not player_id:
                valid = False
                break
            rating = rating_before.get((game_id, player_id))
            if rating is None:
                valid = False
                break
            ratings.append(rating)
            player_ids.append(player_id)
            entry_id = row.get("entry_id")
            seat_positions.append(seat_by_pair.get((game_id, entry_id)) if entry_id else None)
        if not valid or len(ratings) < 2:
            continue

        game_date = parse_datetime_value(rows[0]["start_date"])
        while recent_draw_window and (game_date - recent_draw_window[0][0]).days > 90:
            _, old_draw = recent_draw_window.popleft()
            recent_draw_sum -= old_draw
        global_recent_draw_rate_90d = recent_draw_sum / len(recent_draw_window) if recent_draw_window else 0.0

        raw_round_number = rows[0].get("round_number")
        try:
            round_number = int(raw_round_number) if raw_round_number is not None else None
        except (TypeError, ValueError):
            round_number = None
        if round_number is None:
            continue

        tournament_id = rows[0].get("tournament_id")
        tournament_id_str = str(tournament_id or "")
        current_round_key = round_key_for_rows(rows)
        prior_round_key = last_round_key_by_tournament.get(tournament_id_str)
        if prior_round_key is not None and current_round_key != prior_round_key:
            apply_pending_round_updates(tournament_id_str)
        if tournament_id_str:
            last_round_key_by_tournament[tournament_id_str] = current_round_key
        max_round = max_swiss_round.get(str(tournament_id)) if tournament_id else None
        if round_number is not None and max_round and max_round > 1:
            swiss_progress = (round_number - 1) / (max_round - 1)
            rounds_remaining = max(0, max_round - round_number)
        else:
            swiss_progress = 0.0
            rounds_remaining = 0

        is_draw = 1 if any(str(row.get("result") or "") == "draw" for row in rows) else 0
        sorted_ratings = sorted(ratings, reverse=True)
        mean_elo = sum(ratings) / len(ratings)
        median_elo = float(np.median(np.asarray(ratings, dtype=float)))
        top2_mean_elo = sum(sorted_ratings[:2]) / min(2, len(sorted_ratings))
        top3_mean_elo = sum(sorted_ratings[:3]) / min(3, len(sorted_ratings))
        top1_minus_top2 = sorted_ratings[0] - sorted_ratings[1] if len(sorted_ratings) > 1 else 0.0
        elo_std = float(np.std(np.asarray(ratings, dtype=float)))
        elo_gini = gini(ratings)
        high1550 = sum(1 for rating in ratings if rating >= 1550)
        high1600 = sum(1 for rating in ratings if rating >= 1600)
        high1650 = sum(1 for rating in ratings if rating >= 1650)
        high1700 = sum(1 for rating in ratings if rating >= 1700)
        high1800 = sum(1 for rating in ratings if rating >= 1800)
        highest_idx = max(range(len(ratings)), key=lambda index: ratings[index])
        second_idx = sorted(range(len(ratings)), key=lambda index: ratings[index], reverse=True)[1] if len(ratings) > 1 else highest_idx
        seat_highest = seat_positions[highest_idx] if seat_positions[highest_idx] is not None else -1
        seat_second = seat_positions[second_idx] if seat_positions[second_idx] is not None else -1
        top2_adjacent = 0
        if seat_highest >= 0 and seat_second >= 0 and len(ratings) == 4:
            seat_gap = abs(seat_highest - seat_second)
            top2_adjacent = 1 if seat_gap in (1, 3) else 0

        prior_draw_rates = [
            player_history[player_id][0] / player_history[player_id][1]
            if player_history[player_id][1]
            else 0.0
            for player_id in player_ids
        ]
        prior_win_rates = [
            player_history[player_id][2] / player_history[player_id][1]
            if player_history[player_id][1]
            else 0.0
            for player_id in player_ids
        ]
        prior_decisive_rates = [
            player_history[player_id][3] / player_history[player_id][1]
            if player_history[player_id][1]
            else 0.0
            for player_id in player_ids
        ]
        avg_player_prior_draw = sum(prior_draw_rates) / len(prior_draw_rates)
        median_player_prior_draw = float(np.median(np.asarray(prior_draw_rates, dtype=float))) if prior_draw_rates else 0.0
        min_player_prior_draw = min(prior_draw_rates) if prior_draw_rates else 0.0
        max_player_prior_draw = max(prior_draw_rates) if prior_draw_rates else 0.0
        prior_draw_std = float(np.std(np.asarray(prior_draw_rates, dtype=float))) if prior_draw_rates else 0.0
        prior_draw_range = max_player_prior_draw - min_player_prior_draw if prior_draw_rates else 0.0
        count_high_draw_players = sum(1 for rate in prior_draw_rates if rate >= 0.25)
        count_high_win_low_draw_players = sum(
            1
            for win_rate, draw_rate in zip(prior_win_rates, prior_draw_rates, strict=True)
            if win_rate >= 0.35 and draw_rate <= 0.10
        )
        draw_rate_range_above_threshold = 1 if prior_draw_rates and (max(prior_draw_rates) - min(prior_draw_rates)) >= 0.15 else 0
        avg_player_prior_win = sum(prior_win_rates) / len(prior_win_rates) if prior_win_rates else 0.0
        max_player_prior_win = max(prior_win_rates) if prior_win_rates else 0.0
        avg_player_prior_decisive = sum(prior_decisive_rates) / len(prior_decisive_rates) if prior_decisive_rates else 0.0
        max_player_prior_decisive = max(prior_decisive_rates) if prior_decisive_rates else 0.0

        pair_counts = tournament_pair_meetings[tournament_id_str]
        prior_pair_meetings = []
        global_prior_pair_meetings = []
        for index, player_id in enumerate(player_ids):
            for opponent_id in player_ids[index + 1 :]:
                pair = tuple(sorted((player_id, opponent_id)))
                prior_pair_meetings.append(pair_counts.get(pair, 0))
                global_prior_pair_meetings.append(global_pair_meetings.get(pair, 0))
        prior_pair_meetings_avg = (
            float(sum(prior_pair_meetings) / len(prior_pair_meetings)) if prior_pair_meetings else 0.0
        )
        prior_pair_meetings_max = max(prior_pair_meetings) if prior_pair_meetings else 0
        global_pair_meetings_avg = (
            float(sum(global_prior_pair_meetings) / len(global_prior_pair_meetings)) if global_prior_pair_meetings else 0.0
        )
        global_pair_meetings_max = max(global_prior_pair_meetings) if global_prior_pair_meetings else 0

        field_players = tournament_player_ids.get(tournament_id_str, set())
        field_size = max(len(field_players), len(player_ids), 1)
        current_points_by_player = tournament_points[tournament_id_str]
        current_opponents_by_player = tournament_opponents[tournament_id_str]
        point_values = [current_points_by_player.get(player_id, 0) for player_id in field_players] if field_players else [0]
        point_values.sort(reverse=True)
        points_percentile_map: dict[int, float] = {}
        if field_size <= 1:
            for points in set(point_values):
                points_percentile_map[points] = 1.0
        else:
            by_points: dict[int, list[int]] = defaultdict(list)
            for index, points in enumerate(point_values):
                by_points[points].append(index)
            for points, indexes in by_points.items():
                avg_rank = (indexes[0] + indexes[-1]) / 2.0
                points_percentile_map[points] = 1.0 - (avg_rank / (field_size - 1))
        player_points = [current_points_by_player.get(player_id, 0) for player_id in player_ids]
        player_percentiles = [points_percentile_map.get(points, 0.5) for points in player_points]
        points_std = float(np.std(np.asarray(player_points, dtype=float))) if player_points else 0.0

        top_cut = tournament_cut_sizes.get(tournament_id_str, 0)
        cut_fraction = min(1.0, top_cut / field_size) if top_cut > 0 else 0.0
        cut_size_bucket = 0 if top_cut <= 0 else 1 if top_cut <= 4 else 2 if top_cut <= 8 else 3 if top_cut <= 16 else 4 if top_cut <= 32 else 5
        cut_line_percentile = 1.0 - cut_fraction if cut_fraction > 0 else 1.0
        cut_rank_index = min(max(top_cut - 1, 0), max(len(point_values) - 1, 0)) if point_values else 0
        cut_line_points = point_values[cut_rank_index] if point_values and top_cut > 0 else 0
        history_point_expectations = []
        for field_player_id in field_players:
            total_games = player_history[field_player_id][1]
            if total_games:
                expected_round_points = (5.0 * (player_history[field_player_id][2] / total_games)) + (
                    player_history[field_player_id][0] / total_games
                )
            else:
                expected_round_points = 0.0
            history_point_expectations.append(expected_round_points)
        fallback_round_points = (sum(history_point_expectations) / len(history_point_expectations)) if history_point_expectations else 1.25
        projected_final_points = []
        for field_player_id in field_players:
            total_games = player_history[field_player_id][1]
            if total_games:
                expected_round_points = (5.0 * (player_history[field_player_id][2] / total_games)) + (
                    player_history[field_player_id][0] / total_games
                )
            else:
                expected_round_points = fallback_round_points
            expected_round_points = max(0.0, min(5.0, expected_round_points))
            projected_final_points.append(current_points_by_player.get(field_player_id, 0) + (max(0, rounds_remaining) * expected_round_points))
        projected_final_points.sort(reverse=True)
        expected_cut_line_points = (
            projected_final_points[cut_rank_index] if projected_final_points and top_cut > 0 else float(cut_line_points)
        )
        estimated_omw_by_player: dict[str, float] = {}
        for field_player_id in field_players:
            opponents = current_opponents_by_player.get(field_player_id, set())
            if not opponents:
                estimated_omw_by_player[field_player_id] = 0.0
                continue
            contributions = []
            for opponent_id in opponents:
                total_games = player_history[opponent_id][1]
                win_rate = (player_history[opponent_id][2] / total_games) if total_games else 0.0
                contributions.append(max(win_rate, 0.20))
            estimated_omw_by_player[field_player_id] = sum(contributions) / len(contributions) if contributions else 0.0
        same_points_omw_percentile_by_player: dict[str, float] = {}
        players_by_points: dict[int, list[str]] = defaultdict(list)
        for field_player_id in field_players:
            players_by_points[current_points_by_player.get(field_player_id, 0)].append(field_player_id)
        for cohort in players_by_points.values():
            if len(cohort) <= 1:
                for field_player_id in cohort:
                    same_points_omw_percentile_by_player[field_player_id] = 1.0
                continue
            ordered = sorted(cohort, key=lambda field_player_id: estimated_omw_by_player.get(field_player_id, 0.0), reverse=True)
            size = len(ordered)
            for index, field_player_id in enumerate(ordered):
                same_points_omw_percentile_by_player[field_player_id] = 1.0 - (index / (size - 1))
        tiebreak_seed_by_player = {field_player_id: index for index, field_player_id in enumerate(sorted(field_players))}
        ordered_field_players = sorted(
            field_players,
            key=lambda field_player_id: (
                -current_points_by_player.get(field_player_id, 0),
                -estimated_omw_by_player.get(field_player_id, 0.0),
                tiebreak_seed_by_player[field_player_id],
                str(field_player_id),
            ),
        )
        current_rank_by_player = {field_player_id: index + 1 for index, field_player_id in enumerate(ordered_field_players)}
        draw_secure_rank_by_player = hypothetical_rank_by_player(
            ordered_field_players,
            target_player_ids=player_ids,
            points_by_player=current_points_by_player,
            estimated_omw_by_player=estimated_omw_by_player,
            tiebreak_seed_by_player=tiebreak_seed_by_player,
            point_delta=1,
        )
        win_secure_rank_by_player = hypothetical_rank_by_player(
            ordered_field_players,
            target_player_ids=player_ids,
            points_by_player=current_points_by_player,
            estimated_omw_by_player=estimated_omw_by_player,
            tiebreak_seed_by_player=tiebreak_seed_by_player,
            point_delta=5,
        )
        cut_margins = [percentile - cut_line_percentile for percentile in player_percentiles]
        pod_estimated_omw = [estimated_omw_by_player.get(player_id, 0.0) for player_id in player_ids]
        pod_same_points_omw_percentiles = [
            same_points_omw_percentile_by_player.get(player_id, 1.0) for player_id in player_ids
        ]
        pod_current_ranks = [current_rank_by_player.get(player_id, field_size) for player_id in player_ids]
        pod_draw_secure_ranks = [draw_secure_rank_by_player.get(player_id, field_size) for player_id in player_ids]
        pod_win_secure_ranks = [win_secure_rank_by_player.get(player_id, field_size) for player_id in player_ids]
        omw_std_within_pod = float(np.std(np.asarray(pod_estimated_omw, dtype=float))) if pod_estimated_omw else 0.0
        avg_points_percentile = sum(player_percentiles) / len(player_percentiles)
        max_points_percentile = max(player_percentiles) if player_percentiles else 0.0
        avg_cut_margin = sum(cut_margins) / len(cut_margins) if cut_margins else 0.0
        min_abs_cut_margin = min(abs(margin) for margin in cut_margins) if cut_margins else 1.0
        bubble_margin = max(0.02, 1.0 / field_size)
        points_to_current_cut = [float(points - cut_line_points) for points in player_points]
        points_to_cut = [float(points - expected_cut_line_points) for points in player_points]
        max_future_points = max(0, rounds_remaining) * 5
        count_above_cut_line = sum(1 for margin in cut_margins if margin >= 0.0)
        count_near_cut_line = sum(1 for margin in cut_margins if abs(margin) <= bubble_margin)
        count_locked_for_current_cut = sum(1 for points in player_points if points > cut_line_points + max_future_points)
        count_dead_for_current_cut = sum(1 for points in player_points if points + max_future_points < cut_line_points)
        count_draw_safe_for_current_cut = sum(1 for points in player_points if points + 1 >= cut_line_points)
        count_must_win_for_current_cut = sum(
            1 for points in player_points if (points + 1 < cut_line_points and points + 5 >= cut_line_points)
        )
        all_players_draw_safe_for_current_cut = 1 if player_points and count_draw_safe_for_current_cut == len(player_points) else 0
        count_locked_for_cut = sum(1 for points in player_points if points > expected_cut_line_points + max_future_points)
        count_dead_for_cut = sum(1 for points in player_points if points + max_future_points < expected_cut_line_points)
        count_live_for_cut = len(player_points) - count_locked_for_cut - count_dead_for_cut
        count_draw_safe_for_cut = sum(1 for points in player_points if points + 1 >= expected_cut_line_points)
        count_must_win_for_cut = sum(
            1 for points in player_points if (points + 1 < expected_cut_line_points and points + 5 >= expected_cut_line_points)
        )
        all_players_draw_safe = 1 if player_points and count_draw_safe_for_cut == len(player_points) else 0
        count_currently_in_cut = sum(1 for rank in pod_current_ranks if rank <= top_cut) if top_cut > 0 else 0
        count_currently_outside_cut = len(pod_current_ranks) - count_currently_in_cut
        count_players_currently_safe = count_locked_for_cut
        count_players_currently_dead = count_dead_for_cut
        all_players_live = 1 if player_ids and count_live_for_cut == len(player_ids) else 0
        count_draw_secures_cut = sum(1 for rank in pod_draw_secure_ranks if rank <= top_cut) if top_cut > 0 else 0
        count_win_secures_cut = sum(1 for rank in pod_win_secure_ranks if rank <= top_cut) if top_cut > 0 else 0
        count_must_win_to_stay_live = (
            sum(
                1
                for current_rank, draw_rank, win_rank in zip(
                    pod_current_ranks,
                    pod_draw_secure_ranks,
                    pod_win_secure_ranks,
                    strict=True,
                )
                if current_rank > top_cut and draw_rank > top_cut and win_rank <= top_cut
            )
            if top_cut > 0
            else 0
        )
        all_players_draw_secures_cut = 1 if player_ids and count_draw_secures_cut == len(player_ids) else 0
        mixed_pod_cut_incentives = (
            1
            if top_cut > 0
            and count_draw_secures_cut > 0
            and count_draw_secures_cut < len(player_ids)
            and count_must_win_to_stay_live > 0
            else 0
        )
        some_locked_some_must_win = 1 if count_locked_for_cut > 0 and count_must_win_to_stay_live > 0 else 0
        rank_minus_cut = [float(rank - top_cut) for rank in pod_current_ranks] if top_cut > 0 else [0.0 for _ in pod_current_ranks]
        draw_secure_rank_delta = [float(current - draw_rank) for current, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)]
        win_secure_rank_delta = [float(current - win_rank) for current, win_rank in zip(pod_current_ranks, pod_win_secure_ranks, strict=True)]
        count_bottom_quartile_omw_in_same_points_group = sum(1 for value in pod_same_points_omw_percentiles if value <= 0.25)
        count_players_near_cut_band = sum(1 for rank in pod_current_ranks if top_cut > 0 and abs(rank - top_cut) <= 4)
        is_last_swiss_round = 1 if rounds_remaining == 0 else 0
        is_penultimate_swiss_round = 1 if rounds_remaining == 1 else 0

        tournament_size_raw = tournament_meta.get(str(tournament_id), {}).get("player_count", 0)
        try:
            tournament_size = int(tournament_size_raw) if tournament_size_raw is not None else 0
        except (TypeError, ValueError):
            tournament_size = 0
        size_bucket = 0 if tournament_size < 32 else 1 if tournament_size < 64 else 2 if tournament_size < 128 else 3

        month = game_date.month
        quarter = (month - 1) // 3 + 1
        series_key = tournament_series_keys.get(tournament_id_str, "unknown_series")
        state_key = tournament_state_keys.get(tournament_id_str, "")
        country_key = tournament_country_keys.get(tournament_id_str, "")
        series_draws, series_total = series_history[series_key]
        series_prior_draw_rate = (series_draws / series_total) if series_total else 0.0
        series_events_seen = series_total
        state_draws, state_total = state_history[state_key]
        state_prior_draw_rate = (state_draws / state_total) if state_total and state_key else 0.0
        country_draws, country_total = country_history[country_key]
        country_prior_draw_rate = (country_draws / country_total) if country_total and country_key else 0.0
        series_prior_draw_rate_smoothed_50 = smoothed_rate(series_draws, series_total, global_recent_draw_rate_90d, 50.0)
        series_prior_draw_rate_smoothed_100 = smoothed_rate(series_draws, series_total, global_recent_draw_rate_90d, 100.0)
        series_prior_draw_rate_smoothed_250 = smoothed_rate(series_draws, series_total, global_recent_draw_rate_90d, 250.0)
        series_prior_draw_rate_smoothed_500 = smoothed_rate(series_draws, series_total, global_recent_draw_rate_90d, 500.0)
        series_events_seen_log = float(np.log1p(series_total))

        player_prior_games = [player_history[player_id][1] for player_id in player_ids]
        player_prior_draws = [player_history[player_id][0] for player_id in player_ids]
        smoothed_player_draw_rates = [
            smoothed_rate(draws, games, global_recent_draw_rate_90d, 50.0)
            for draws, games in zip(player_prior_draws, player_prior_games, strict=True)
        ]
        avg_player_prior_games = float(sum(player_prior_games) / len(player_prior_games)) if player_prior_games else 0.0
        min_player_prior_games = float(min(player_prior_games)) if player_prior_games else 0.0
        player_prior_confidence_avg = (
            float(sum(games / (games + 50.0) for games in player_prior_games) / len(player_prior_games))
            if player_prior_games
            else 0.0
        )

        draw_as_good_as_win = [
            (draw_rank <= top_cut) == (win_rank <= top_cut) if top_cut > 0 else True
            for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
        ]
        loss_eliminates = [
            points + max_future_points < expected_cut_line_points
            for points in player_points
        ]
        draw_preserves_cut_rank = [
            current_rank <= top_cut and draw_rank <= top_cut
            for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
        ] if top_cut > 0 else []
        win_changes_cut_status = [
            (current_rank <= top_cut) != (win_rank <= top_cut)
            for current_rank, win_rank in zip(pod_current_ranks, pod_win_secure_ranks, strict=True)
        ] if top_cut > 0 else []

        points_by_value: dict[int, int] = defaultdict(int)
        for points in player_points:
            points_by_value[points] += 1
        same_points_count_in_pod = max(points_by_value.values()) if points_by_value else 0
        min_points_in_pod = min(player_points) if player_points else 0
        max_points_in_pod = max(player_points) if player_points else 0
        points_range_within_pod = max_points_in_pod - min_points_in_pod
        all_players_above_projected_cut_line = 1 if player_points and all(points >= expected_cut_line_points for points in player_points) else 0
        all_players_within_one_point_of_cut_line = 1 if player_points and all(abs(points - expected_cut_line_points) <= 1 for points in player_points) else 0

        round_size_cut_key = (round_number if round_number is not None else -1, size_bucket, cut_size_bucket)
        round_size_cut_draws, round_size_cut_total = round_size_cut_history[round_size_cut_key]
        round_size_cut_prior_draw_rate_smoothed_100 = smoothed_rate(
            round_size_cut_draws,
            round_size_cut_total,
            global_recent_draw_rate_90d,
            100.0,
        )
        series_pod_size_key = (series_key, len(rows))
        series_pod_size_draws, series_pod_size_total = series_pod_size_history[series_pod_size_key]
        series_pod_size_prior_draw_rate_smoothed_100 = smoothed_rate(
            series_pod_size_draws,
            series_pod_size_total,
            global_recent_draw_rate_90d,
            100.0,
        )
        is_swiss = 1 if round_number is not None else 0
        series_swiss_key = (series_key, is_swiss)
        series_swiss_draws, series_swiss_total = series_swiss_history[series_swiss_key]
        series_swiss_prior_draw_rate_smoothed_100 = smoothed_rate(
            series_swiss_draws,
            series_swiss_total,
            global_recent_draw_rate_90d,
            100.0,
        )
        decisive_entropy, decisive_max, decisive_min, decisive_spread = decisive_probability_features(ratings)
        count_repeat_pairs = sum(1 for count in prior_pair_meetings if count > 0)
        count_players_with_no_history = sum(1 for games in player_prior_games if games == 0)
        count_players_with_low_history = sum(1 for games in player_prior_games if games < 10)
        count_default_elos = sum(1 for rating in ratings if abs(rating - 1500.0) < 1e-9)
        min_draw_secure_rank = min(pod_draw_secure_ranks) if pod_draw_secure_ranks else 0
        max_draw_secure_rank = max(pod_draw_secure_ranks) if pod_draw_secure_ranks else 0
        bye_rank = topdeck_bye_rank(top_cut)
        bye_fraction = (bye_rank / field_size) if bye_rank else 0.0
        bye_rank_index = min(max((bye_rank or 1) - 1, 0), max(len(point_values) - 1, 0)) if point_values else 0
        bye_line_points = point_values[bye_rank_index] if bye_rank and point_values else 0
        expected_bye_line_points = (
            projected_final_points[bye_rank_index] if bye_rank and projected_final_points else 0.0
        )
        pod_loss_ranks = pod_current_ranks
        count_currently_in_bye = sum(1 for rank in pod_current_ranks if bye_rank and rank <= bye_rank)
        count_draw_secures_bye = sum(1 for rank in pod_draw_secure_ranks if bye_rank and rank <= bye_rank)
        count_win_secures_bye = sum(1 for rank in pod_win_secure_ranks if bye_rank and rank <= bye_rank)
        count_must_win_for_bye = sum(
            1
            for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
            if bye_rank and draw_rank > bye_rank and win_rank <= bye_rank
        )
        count_players_win_only_live = sum(
            1
            for draw_rank, win_rank in zip(pod_draw_secure_ranks, pod_win_secure_ranks, strict=True)
            if top_cut > 0 and draw_rank > top_cut and win_rank <= top_cut
        )
        count_players_win_only_live_for_bye = count_must_win_for_bye
        all_players_draw_lock_cut = 1 if top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= top_cut else 0
        all_players_draw_lock_bye = 1 if bye_rank and pod_draw_secure_ranks and max_draw_secure_rank <= bye_rank else 0
        min_draw_rank_margin_to_cut = (
            min(float(top_cut - rank) for rank in pod_draw_secure_ranks)
            if top_cut > 0 and pod_draw_secure_ranks
            else 0.0
        )
        min_draw_rank_margin_to_bye = (
            min(float(bye_rank - rank) for rank in pod_draw_secure_ranks)
            if bye_rank and pod_draw_secure_ranks
            else 0.0
        )
        count_players_draw_makes_cut = sum(
            1
            for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
            if top_cut > 0 and current_rank > top_cut and draw_rank <= top_cut
        )
        count_players_draw_makes_bye = sum(
            1
            for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True)
            if bye_rank and current_rank > bye_rank and draw_rank <= bye_rank
        )
        draw_hurts_any_player_cut_status = (
            1
            if top_cut > 0
            and any(current_rank <= top_cut and draw_rank > top_cut for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True))
            else 0
        )
        draw_hurts_any_player_bye_status = (
            1
            if bye_rank
            and any(current_rank <= bye_rank and draw_rank > bye_rank for current_rank, draw_rank in zip(pod_current_ranks, pod_draw_secure_ranks, strict=True))
            else 0
        )
        draw_hurts_any_player_status = 1 if draw_hurts_any_player_cut_status or draw_hurts_any_player_bye_status else 0
        all_players_above_cut_after_draw = all_players_draw_lock_cut
        all_players_above_bye_after_draw = all_players_draw_lock_bye
        all_players_above_cut_after_loss = 1 if top_cut > 0 and pod_loss_ranks and max(pod_loss_ranks) <= top_cut else 0
        all_players_above_bye_after_loss = 1 if bye_rank and pod_loss_ranks and max(pod_loss_ranks) <= bye_rank else 0
        pod_has_asymmetric_cut_incentive = 1 if top_cut > 0 and count_draw_secures_cut > 0 and count_draw_secures_cut < len(player_ids) else 0
        pod_has_asymmetric_bye_incentive = 1 if bye_rank and count_draw_secures_bye > 0 and count_draw_secures_bye < len(player_ids) else 0
        pod_has_asymmetric_incentive = 1 if pod_has_asymmetric_cut_incentive or pod_has_asymmetric_bye_incentive else 0
        draw_cut_status = [rank <= top_cut if top_cut > 0 else False for rank in pod_draw_secure_ranks]
        win_cut_status = [rank <= top_cut if top_cut > 0 else False for rank in pod_win_secure_ranks]
        draw_bye_status = [rank <= bye_rank if bye_rank else False for rank in pod_draw_secure_ranks]
        win_bye_status = [rank <= bye_rank if bye_rank else False for rank in pod_win_secure_ranks]
        player_draw_as_good_as_win = [
            (draw_cut == win_cut) and (draw_bye == win_bye)
            for draw_cut, win_cut, draw_bye, win_bye in zip(draw_cut_status, win_cut_status, draw_bye_status, win_bye_status, strict=True)
        ]
        draw_vs_win_status_same_count = sum(1 for value in player_draw_as_good_as_win if value)
        pairwise_mutual_draw_benefit_count = 0
        for left_index in range(len(player_draw_as_good_as_win)):
            for right_index in range(left_index + 1, len(player_draw_as_good_as_win)):
                if player_draw_as_good_as_win[left_index] and player_draw_as_good_as_win[right_index]:
                    pairwise_mutual_draw_benefit_count += 1
        count_players_draw_as_good_as_win_for_bye = sum(
            1
            for draw_status, win_status in zip(draw_bye_status, win_bye_status, strict=True)
            if bye_rank and draw_status == win_status
        )
        first_row = rows[0]

        pods.append(
            DrawPodRow(
                game_id=game_id,
                date=game_date,
                is_draw=is_draw,
                is_swiss=is_swiss,
                pod_size=len(rows),
                spread=max(ratings) - min(ratings),
                mean_elo=mean_elo,
                median_elo=median_elo,
                top2_mean_elo=top2_mean_elo,
                top3_mean_elo=top3_mean_elo,
                top1_minus_top2=top1_minus_top2,
                elo_std=elo_std,
                elo_gini=elo_gini,
                high1550=high1550,
                high1600=high1600,
                high1650=high1650,
                high1700=high1700,
                high1800=high1800,
                seat_highest=seat_highest,
                seat_second=seat_second,
                top2_adjacent=top2_adjacent,
                swiss_progress=swiss_progress,
                round_number=round_number if round_number is not None else -1,
                rounds_remaining=rounds_remaining,
                cut_fraction=cut_fraction,
                cut_size_bucket=cut_size_bucket,
                current_cut_line_points=float(cut_line_points),
                expected_cut_line_points=expected_cut_line_points,
                avg_estimated_omw=(sum(pod_estimated_omw) / len(pod_estimated_omw)) if pod_estimated_omw else 0.0,
                min_estimated_omw=min(pod_estimated_omw) if pod_estimated_omw else 0.0,
                max_estimated_omw=max(pod_estimated_omw) if pod_estimated_omw else 0.0,
                omw_std_within_pod=omw_std_within_pod,
                avg_same_points_omw_percentile=(
                    sum(pod_same_points_omw_percentiles) / len(pod_same_points_omw_percentiles)
                ) if pod_same_points_omw_percentiles else 0.0,
                min_same_points_omw_percentile=min(pod_same_points_omw_percentiles) if pod_same_points_omw_percentiles else 0.0,
                max_same_points_omw_percentile=max(pod_same_points_omw_percentiles) if pod_same_points_omw_percentiles else 0.0,
                count_bottom_quartile_omw_in_same_points_group=count_bottom_quartile_omw_in_same_points_group,
                count_currently_in_cut=count_currently_in_cut,
                count_currently_outside_cut=count_currently_outside_cut,
                count_players_currently_safe=count_players_currently_safe,
                count_players_currently_dead=count_players_currently_dead,
                all_players_live=all_players_live,
                count_draw_secures_cut=count_draw_secures_cut,
                count_win_secures_cut=count_win_secures_cut,
                count_must_win_to_stay_live=count_must_win_to_stay_live,
                all_players_draw_secures_cut=all_players_draw_secures_cut,
                mixed_pod_cut_incentives=mixed_pod_cut_incentives,
                some_locked_some_must_win=some_locked_some_must_win,
                avg_rank_minus_cut=(sum(rank_minus_cut) / len(rank_minus_cut)) if rank_minus_cut else 0.0,
                min_rank_minus_cut=min(rank_minus_cut) if rank_minus_cut else 0.0,
                rank_spread_within_pod=(max(pod_current_ranks) - min(pod_current_ranks)) if pod_current_ranks else 0,
                avg_draw_secure_rank_delta=(sum(draw_secure_rank_delta) / len(draw_secure_rank_delta)) if draw_secure_rank_delta else 0.0,
                avg_win_secure_rank_delta=(sum(win_secure_rank_delta) / len(win_secure_rank_delta)) if win_secure_rank_delta else 0.0,
                avg_points_percentile=avg_points_percentile,
                max_points_percentile=max_points_percentile,
                points_std=points_std,
                avg_cut_margin=avg_cut_margin,
                min_abs_cut_margin=min_abs_cut_margin,
                avg_points_to_current_cut=(sum(points_to_current_cut) / len(points_to_current_cut)) if points_to_current_cut else 0.0,
                min_points_to_current_cut=min(points_to_current_cut) if points_to_current_cut else 0.0,
                avg_points_to_cut=(sum(points_to_cut) / len(points_to_cut)) if points_to_cut else 0.0,
                min_points_to_cut=min(points_to_cut) if points_to_cut else 0.0,
                count_above_cut_line=count_above_cut_line,
                count_near_cut_line=count_near_cut_line,
                count_locked_for_current_cut=count_locked_for_current_cut,
                count_dead_for_current_cut=count_dead_for_current_cut,
                count_draw_safe_for_current_cut=count_draw_safe_for_current_cut,
                count_must_win_for_current_cut=count_must_win_for_current_cut,
                all_players_draw_safe_for_current_cut=all_players_draw_safe_for_current_cut,
                count_locked_for_cut=count_locked_for_cut,
                count_dead_for_cut=count_dead_for_cut,
                count_live_for_cut=count_live_for_cut,
                count_draw_safe_for_cut=count_draw_safe_for_cut,
                count_must_win_for_cut=count_must_win_for_cut,
                all_players_draw_safe=all_players_draw_safe,
                is_last_swiss_round=is_last_swiss_round,
                is_penultimate_swiss_round=is_penultimate_swiss_round,
                month=month,
                quarter=quarter,
                tournament_size=tournament_size,
                size_bucket=size_bucket,
                global_recent_draw_rate_90d=global_recent_draw_rate_90d,
                avg_player_prior_draw=avg_player_prior_draw,
                median_player_prior_draw=median_player_prior_draw,
                min_player_prior_draw=min_player_prior_draw,
                max_player_prior_draw=max_player_prior_draw,
                prior_draw_std=prior_draw_std,
                prior_draw_range=prior_draw_range,
                count_high_draw_players=count_high_draw_players,
                count_high_win_low_draw_players=count_high_win_low_draw_players,
                draw_rate_range_above_threshold=draw_rate_range_above_threshold,
                avg_player_prior_win=avg_player_prior_win,
                max_player_prior_win=max_player_prior_win,
                avg_player_prior_decisive=avg_player_prior_decisive,
                max_player_prior_decisive=max_player_prior_decisive,
                prior_pair_meetings_avg=prior_pair_meetings_avg,
                prior_pair_meetings_max=prior_pair_meetings_max,
                global_pair_meetings_avg=global_pair_meetings_avg,
                global_pair_meetings_max=global_pair_meetings_max,
                series_prior_draw_rate=series_prior_draw_rate,
                series_events_seen=series_events_seen,
                state_prior_draw_rate=state_prior_draw_rate,
                country_prior_draw_rate=country_prior_draw_rate,
                count_players_near_cut_band=count_players_near_cut_band,
                tournament_id=tournament_id_str,
                tournament_name=str(tournament_meta.get(str(tournament_id), {}).get("name") or ""),
                series_key=series_key,
                round_name=str(first_row.get("round_name") or ""),
                table_number=parse_int(first_row.get("table_number"), -1),
                series_prior_draw_rate_smoothed_50=series_prior_draw_rate_smoothed_50,
                series_prior_draw_rate_smoothed_100=series_prior_draw_rate_smoothed_100,
                series_prior_draw_rate_smoothed_250=series_prior_draw_rate_smoothed_250,
                series_prior_draw_rate_smoothed_500=series_prior_draw_rate_smoothed_500,
                series_events_seen_log=series_events_seen_log,
                avg_player_prior_draw_smoothed_50=(sum(smoothed_player_draw_rates) / len(smoothed_player_draw_rates)) if smoothed_player_draw_rates else 0.0,
                median_player_prior_draw_smoothed_50=float(np.median(np.asarray(smoothed_player_draw_rates, dtype=float))) if smoothed_player_draw_rates else 0.0,
                max_player_prior_draw_smoothed_50=max(smoothed_player_draw_rates) if smoothed_player_draw_rates else 0.0,
                avg_player_prior_games=avg_player_prior_games,
                min_player_prior_games=min_player_prior_games,
                player_prior_confidence_avg=player_prior_confidence_avg,
                all_players_can_draw_into_cut=all_players_draw_safe,
                any_player_eliminated_by_draw=1 if count_must_win_to_stay_live > 0 else 0,
                all_players_locked_with_draw=all_players_draw_secures_cut,
                count_players_draw_as_good_as_win=sum(1 for value in draw_as_good_as_win if value),
                count_players_loss_eliminates=sum(1 for value in loss_eliminates if value),
                draw_preserves_cut_rank_count=sum(1 for value in draw_preserves_cut_rank if value),
                win_changes_cut_status_count=sum(1 for value in win_changes_cut_status if value),
                same_points_count_in_pod=same_points_count_in_pod,
                all_players_same_points=1 if player_points and same_points_count_in_pod == len(player_points) else 0,
                points_range_within_pod=points_range_within_pod,
                min_points_in_pod=min_points_in_pod,
                max_points_in_pod=max_points_in_pod,
                all_players_above_projected_cut_line=all_players_above_projected_cut_line,
                all_players_within_one_point_of_cut_line=all_players_within_one_point_of_cut_line,
                last_round_cut_fraction=cut_fraction if is_last_swiss_round else 0.0,
                penultimate_round_cut_fraction=cut_fraction if is_penultimate_swiss_round else 0.0,
                round_number_size_bucket=float((round_number if round_number is not None else -1) * (size_bucket + 1)),
                last_round_size_bucket=size_bucket if is_last_swiss_round else 0,
                round_size_cut_bucket_key=((round_number if round_number is not None else -1) * 100) + (size_bucket * 10) + cut_size_bucket,
                round_size_cut_prior_draw_rate_smoothed_100=round_size_cut_prior_draw_rate_smoothed_100,
                decisive_win_probability_entropy=decisive_entropy,
                max_decisive_win_probability=decisive_max,
                min_decisive_win_probability=decisive_min,
                decisive_win_probability_spread=decisive_spread,
                any_repeat_pair=1 if count_repeat_pairs > 0 else 0,
                count_repeat_pairs=count_repeat_pairs,
                pod_size_round_number=float(len(rows) * (round_number if round_number is not None else -1)),
                pod_size_is_last_swiss_round=len(rows) if is_last_swiss_round else 0,
                pod_size_cut_fraction=float(len(rows) * cut_fraction),
                pod_size_series_prior_draw_rate=float(len(rows) * series_prior_draw_rate),
                series_pod_size_prior_draw_rate_smoothed_100=series_pod_size_prior_draw_rate_smoothed_100,
                series_swiss_prior_draw_rate_smoothed_100=series_swiss_prior_draw_rate_smoothed_100,
                series_prior_draw_rate_residual=series_prior_draw_rate - global_recent_draw_rate_90d,
                count_players_with_no_history=count_players_with_no_history,
                count_players_with_low_history=count_players_with_low_history,
                all_elos_default=1 if ratings and count_default_elos == len(ratings) else 0,
                count_default_elos=count_default_elos,
                seat_data_missing=1 if any((game_id, row.get("entry_id")) not in seat_by_pair for row in rows) else 0,
                min_draw_secure_rank=min_draw_secure_rank,
                max_draw_secure_rank=max_draw_secure_rank,
                draw_secure_rank_spread=max_draw_secure_rank - min_draw_secure_rank,
                all_players_draw_rank_within_cut_plus_4=1 if top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= top_cut + 4 else 0,
                all_players_draw_rank_within_cut_plus_8=1 if top_cut > 0 and pod_draw_secure_ranks and max_draw_secure_rank <= top_cut + 8 else 0,
                bye_fraction=bye_fraction,
                bye_line_points=float(bye_line_points),
                expected_bye_line_points=float(expected_bye_line_points),
                count_currently_in_bye=count_currently_in_bye,
                count_draw_secures_bye=count_draw_secures_bye,
                count_win_secures_bye=count_win_secures_bye,
                count_must_win_for_bye=count_must_win_for_bye,
                count_players_win_only_live=count_players_win_only_live,
                count_players_win_only_live_for_bye=count_players_win_only_live_for_bye,
                all_players_draw_lock_cut=all_players_draw_lock_cut,
                all_players_draw_lock_bye=all_players_draw_lock_bye,
                min_draw_rank_margin_to_cut=min_draw_rank_margin_to_cut,
                min_draw_rank_margin_to_bye=min_draw_rank_margin_to_bye,
                count_players_draw_makes_cut=count_players_draw_makes_cut,
                count_players_draw_makes_bye=count_players_draw_makes_bye,
                draw_hurts_any_player_cut_status=draw_hurts_any_player_cut_status,
                draw_hurts_any_player_bye_status=draw_hurts_any_player_bye_status,
                draw_hurts_any_player_status=draw_hurts_any_player_status,
                all_players_above_cut_after_draw=all_players_above_cut_after_draw,
                all_players_above_bye_after_draw=all_players_above_bye_after_draw,
                all_players_above_cut_after_loss=all_players_above_cut_after_loss,
                all_players_above_bye_after_loss=all_players_above_bye_after_loss,
                pod_has_asymmetric_cut_incentive=pod_has_asymmetric_cut_incentive,
                pod_has_asymmetric_bye_incentive=pod_has_asymmetric_bye_incentive,
                pod_has_asymmetric_incentive=pod_has_asymmetric_incentive,
                draw_vs_win_status_same_count=draw_vs_win_status_same_count,
                pairwise_mutual_draw_benefit_count=pairwise_mutual_draw_benefit_count,
                count_players_draw_as_good_as_win_for_bye=count_players_draw_as_good_as_win_for_bye,
            )
        )

        recent_draw_window.append((game_date, is_draw))
        recent_draw_sum += is_draw
        for player_id in player_ids:
            player_history[player_id][0] += is_draw
            player_history[player_id][1] += 1
            player_history[player_id][2] += 1 if next((row.get("result") for row in rows if row.get("player_id") == player_id), None) == "win" else 0
            player_history[player_id][3] += 0 if is_draw else 1
            pending_round_updates[tournament_id_str][player_id] += score_delta(
                next((row.get("result") for row in rows if row.get("player_id") == player_id), None)
            )
        for index, player_id in enumerate(player_ids):
            for opponent_id in player_ids[index + 1 :]:
                pending_round_pair_updates[tournament_id_str].append(tuple(sorted((player_id, opponent_id))))
        series_history[series_key][0] += is_draw
        series_history[series_key][1] += 1
        if state_key:
            state_history[state_key][0] += is_draw
            state_history[state_key][1] += 1
        if country_key:
            country_history[country_key][0] += is_draw
            country_history[country_key][1] += 1
        round_size_cut_history[round_size_cut_key][0] += is_draw
        round_size_cut_history[round_size_cut_key][1] += 1
        series_pod_size_history[series_pod_size_key][0] += is_draw
        series_pod_size_history[series_pod_size_key][1] += 1
        series_swiss_history[series_swiss_key][0] += is_draw
        series_swiss_history[series_swiss_key][1] += 1

    for tournament_id_str in list(pending_round_updates):
        apply_pending_round_updates(tournament_id_str)

    return pods


def score_probs(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, float]:
    clipped = np.clip(probabilities.astype(float), 1e-9, 1 - 1e-9)
    labels = y_true.astype(float)
    log_loss = float(np.mean(-(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped))))
    brier = float(np.mean((clipped - labels) ** 2))
    return log_loss, brier


def recency_weight(game_date: datetime, reference_date: datetime, half_life: int) -> float:
    age_days = max(0.0, (reference_date - game_date).total_seconds() / 86_400.0)
    return 0.5 ** (age_days / half_life)


def make_xy(rows: list[DrawPodRow], features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x_matrix = np.asarray([[getattr(row, feature) for feature in features] for row in rows], dtype=float)
    y_vector = np.asarray([row.is_draw for row in rows], dtype=int)
    return x_matrix, y_vector


def rolling_folds(rows: list[DrawPodRow]) -> list[tuple[list[DrawPodRow], list[DrawPodRow]]]:
    count = len(rows)
    fold_specs = [
        (int(count * 0.4), int(count * 0.5)),
        (int(count * 0.5), int(count * 0.6)),
        (int(count * 0.6), int(count * 0.7)),
    ]
    return [(rows[:train_end], rows[train_end:validation_end]) for train_end, validation_end in fold_specs]


def evaluate_feature_sets(
    folds: list[tuple[list[DrawPodRow], list[DrawPodRow]]],
    feature_sets: dict[str, list[str]],
    *,
    half_life: int,
    base_params: dict[str, Any],
) -> list[tuple[float, float, str, list[str]]]:
    results: list[tuple[float, float, str, list[str]]] = []
    for name, features in feature_sets.items():
        fold_scores: list[tuple[float, float]] = []
        for train_rows, validation_rows in folds:
            x_train, y_train = make_xy(train_rows, features)
            x_validation, y_validation = make_xy(validation_rows, features)
            sample_weight = np.asarray(
                [recency_weight(row.date, train_rows[-1].date, half_life) for row in train_rows],
                dtype=float,
            )
            model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **base_params)
            model.fit(x_train, y_train, sample_weight=sample_weight)
            probabilities = model.predict_proba(x_validation)[:, 1]
            fold_scores.append(score_probs(y_validation, probabilities))
        results.append(
            (
                float(np.mean([score[0] for score in fold_scores])),
                float(np.mean([score[1] for score in fold_scores])),
                name,
                features,
            )
        )
    return sorted(results, key=lambda item: (item[0], item[1]))


def stable_series_fold(series_key: str, fold_count: int) -> int:
    digest = hashlib.sha256((series_key or "unknown_series").encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % fold_count


def evaluate_series_holdout_feature_sets(
    rows: list[DrawPodRow],
    feature_sets: dict[str, list[str]],
    *,
    fold_count: int,
    half_life: int,
    base_params: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, features in feature_sets.items():
        fold_scores: list[tuple[float, float, int, int]] = []
        for fold_index in range(fold_count):
            train_rows = [row for row in rows if stable_series_fold(row.series_key, fold_count) != fold_index]
            validation_rows = [row for row in rows if stable_series_fold(row.series_key, fold_count) == fold_index]
            if not train_rows or not validation_rows:
                continue
            x_train, y_train = make_xy(train_rows, features)
            x_validation, y_validation = make_xy(validation_rows, features)
            sample_weight = np.asarray(
                [recency_weight(row.date, train_rows[-1].date, half_life) for row in train_rows],
                dtype=float,
            )
            model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **base_params)
            model.fit(x_train, y_train, sample_weight=sample_weight)
            probabilities = model.predict_proba(x_validation)[:, 1]
            log_loss, brier = score_probs(y_validation, probabilities)
            fold_scores.append((log_loss, brier, len(train_rows), len(validation_rows)))
        if not fold_scores:
            continue
        results.append(
            {
                "feature_set": name,
                "avg_series_holdout_log_loss": float(np.mean([score[0] for score in fold_scores])),
                "avg_series_holdout_brier": float(np.mean([score[1] for score in fold_scores])),
                "folds": [
                    {
                        "log_loss": log_loss,
                        "brier": brier,
                        "train_rows": train_count,
                        "validation_rows": validation_count,
                    }
                    for log_loss, brier, train_count, validation_count in fold_scores
                ],
            }
        )
    return sorted(results, key=lambda item: (item["avg_series_holdout_log_loss"], item["avg_series_holdout_brier"]))


def tune_hgb_holdout(
    train_rows: list[DrawPodRow],
    validation_rows: list[DrawPodRow],
    features: list[str],
) -> list[tuple[float, float, int, dict[str, Any]]]:
    half_lives = [75, 90, 105, 120]
    learning_rates = [0.06, 0.08, 0.10]
    max_leaf_nodes_options = [24, 31, 40]
    min_samples_leaf_options = [150, 250, 350]
    l2_options = [0.0, 0.1, 1.0]

    x_train, y_train = make_xy(train_rows, features)
    x_validation, y_validation = make_xy(validation_rows, features)
    results: list[tuple[float, float, int, dict[str, Any]]] = []

    for half_life in half_lives:
        sample_weight = np.asarray(
            [recency_weight(row.date, train_rows[-1].date, half_life) for row in train_rows],
            dtype=float,
        )
        for learning_rate in learning_rates:
            for max_leaf_nodes in max_leaf_nodes_options:
                for min_samples_leaf in min_samples_leaf_options:
                    for l2_regularization in l2_options:
                        params = {
                            "learning_rate": learning_rate,
                            "max_leaf_nodes": max_leaf_nodes,
                            "min_samples_leaf": min_samples_leaf,
                            "max_depth": None,
                            "l2_regularization": l2_regularization,
                        }
                        model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **params)
                        model.fit(x_train, y_train, sample_weight=sample_weight)
                        probabilities = model.predict_proba(x_validation)[:, 1]
                        log_loss, brier = score_probs(y_validation, probabilities)
                        results.append((log_loss, brier, half_life, params))
    return sorted(results, key=lambda item: (item[0], item[1]))


def evaluate_finalists_rolling(
    folds: list[tuple[list[DrawPodRow], list[DrawPodRow]]],
    features: list[str],
    finalists: list[tuple[float, float, int, dict[str, Any]]],
) -> list[tuple[float, float, int, dict[str, Any]]]:
    results: list[tuple[float, float, int, dict[str, Any]]] = []
    for _, _, half_life, params in finalists:
        fold_scores: list[tuple[float, float]] = []
        for train_rows, validation_rows in folds:
            x_train, y_train = make_xy(train_rows, features)
            x_validation, y_validation = make_xy(validation_rows, features)
            sample_weight = np.asarray(
                [recency_weight(row.date, train_rows[-1].date, half_life) for row in train_rows],
                dtype=float,
            )
            model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **params)
            model.fit(x_train, y_train, sample_weight=sample_weight)
            probabilities = model.predict_proba(x_validation)[:, 1]
            fold_scores.append(score_probs(y_validation, probabilities))
        results.append(
            (
                float(np.mean([score[0] for score in fold_scores])),
                float(np.mean([score[1] for score in fold_scores])),
                half_life,
                params,
            )
        )
    return sorted(results, key=lambda item: (item[0], item[1]))


def compare_tree_families(
    development_rows: list[DrawPodRow],
    test_rows: list[DrawPodRow],
    features: list[str],
    half_life: int,
    hgb_params: dict[str, Any],
) -> list[tuple[float, float, str, dict[str, Any]]]:
    x_dev, y_dev = make_xy(development_rows, features)
    x_test, y_test = make_xy(test_rows, features)
    sample_weight = np.asarray(
        [recency_weight(row.date, development_rows[-1].date, half_life) for row in development_rows],
        dtype=float,
    )

    candidates: list[tuple[str, Any]] = [
        ("hgb", HistGradientBoostingClassifier(loss="log_loss", random_state=0, **hgb_params)),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=5,
                max_features="sqrt",
                n_jobs=-1,
                random_state=0,
            ),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=600,
                max_depth=None,
                min_samples_leaf=10,
                max_features="sqrt",
                n_jobs=-1,
                random_state=0,
            ),
        ),
        (
            "et",
            ExtraTreesClassifier(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=5,
                max_features="sqrt",
                n_jobs=-1,
                random_state=0,
            ),
        ),
        (
            "et",
            ExtraTreesClassifier(
                n_estimators=600,
                max_depth=None,
                min_samples_leaf=10,
                max_features="sqrt",
                n_jobs=-1,
                random_state=0,
            ),
        ),
    ]

    reports: list[tuple[float, float, str, dict[str, Any]]] = []
    for family, model in candidates:
        model.fit(x_dev, y_dev, sample_weight=sample_weight)
        probabilities = model.predict_proba(x_test)[:, 1]
        log_loss, brier = score_probs(y_test, probabilities)
        reports.append((log_loss, brier, family, model.get_params()))
    return sorted(reports, key=lambda item: (item[0], item[1]))


def compute_permutation_importance(
    model: HistGradientBoostingClassifier,
    x_test: np.ndarray,
    y_test: np.ndarray,
    features: list[str],
) -> list[tuple[str, float]]:
    random_state = np.random.RandomState(0)
    subset_indices = random_state.choice(len(x_test), size=min(5000, len(x_test)), replace=False)
    importance = permutation_importance(
        model,
        x_test[subset_indices],
        y_test[subset_indices],
        n_repeats=3,
        random_state=0,
        scoring="neg_log_loss",
    )
    pairs = zip(features, importance.importances_mean.tolist(), strict=False)
    return sorted(((feature, score) for feature, score in pairs), key=lambda item: item[1], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument(
        "--raw-data-cache-dir",
        help="Optional directory for cached raw Supabase table snapshots used while rebuilding the rich pod cache.",
    )
    parser.add_argument(
        "--force-feature-set",
        help="Train the final model with this named feature set instead of selecting the best pruning result.",
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

    count = len(pods)
    development_end = int(count * 0.8)
    train_end = int(count * 0.7)
    train_rows = pods[:train_end]
    validation_rows = pods[train_end:development_end]
    development_rows = pods[:development_end]
    test_rows = pods[development_end:]
    folds = rolling_folds(development_rows)
    print(f"Prepared rolling folds: {[(len(train), len(validation)) for train, validation in folds]}", flush=True)

    full_features = [
        "pod_size",
        "spread",
        "mean_elo",
        "median_elo",
        "top2_mean_elo",
        "top3_mean_elo",
        "top1_minus_top2",
        "elo_std",
        "elo_gini",
        "high1550",
        "high1600",
        "high1650",
        "high1700",
        "high1800",
        "seat_highest",
        "seat_second",
        "top2_adjacent",
        "swiss_progress",
        "round_number",
        "rounds_remaining",
        "cut_fraction",
        "cut_size_bucket",
        "current_cut_line_points",
        "expected_cut_line_points",
        "avg_estimated_omw",
        "min_estimated_omw",
        "max_estimated_omw",
        "omw_std_within_pod",
        "avg_same_points_omw_percentile",
        "min_same_points_omw_percentile",
        "max_same_points_omw_percentile",
        "count_bottom_quartile_omw_in_same_points_group",
        "count_currently_in_cut",
        "count_currently_outside_cut",
        "count_players_currently_safe",
        "count_players_currently_dead",
        "all_players_live",
        "count_draw_secures_cut",
        "count_win_secures_cut",
        "count_must_win_to_stay_live",
        "all_players_draw_secures_cut",
        "mixed_pod_cut_incentives",
        "some_locked_some_must_win",
        "avg_rank_minus_cut",
        "min_rank_minus_cut",
        "rank_spread_within_pod",
        "avg_draw_secure_rank_delta",
        "avg_win_secure_rank_delta",
        "avg_points_percentile",
        "max_points_percentile",
        "points_std",
        "avg_cut_margin",
        "min_abs_cut_margin",
        "avg_points_to_current_cut",
        "min_points_to_current_cut",
        "avg_points_to_cut",
        "min_points_to_cut",
        "count_above_cut_line",
        "count_near_cut_line",
        "count_locked_for_current_cut",
        "count_dead_for_current_cut",
        "count_draw_safe_for_current_cut",
        "count_must_win_for_current_cut",
        "all_players_draw_safe_for_current_cut",
        "count_locked_for_cut",
        "count_dead_for_cut",
        "count_live_for_cut",
        "count_draw_safe_for_cut",
        "count_must_win_for_cut",
        "all_players_draw_safe",
        "is_last_swiss_round",
        "is_penultimate_swiss_round",
        "month",
        "quarter",
        "tournament_size",
        "size_bucket",
        "global_recent_draw_rate_90d",
        "avg_player_prior_draw",
        "median_player_prior_draw",
        "min_player_prior_draw",
        "max_player_prior_draw",
        "prior_draw_std",
        "prior_draw_range",
        "count_high_draw_players",
        "count_high_win_low_draw_players",
        "draw_rate_range_above_threshold",
        "avg_player_prior_win",
        "max_player_prior_win",
        "avg_player_prior_decisive",
        "max_player_prior_decisive",
        "prior_pair_meetings_avg",
        "prior_pair_meetings_max",
        "global_pair_meetings_avg",
        "global_pair_meetings_max",
        "series_prior_draw_rate",
        "series_events_seen",
        "state_prior_draw_rate",
        "country_prior_draw_rate",
        "count_players_near_cut_band",
        "series_prior_draw_rate_smoothed_50",
        "series_prior_draw_rate_smoothed_100",
        "series_prior_draw_rate_smoothed_250",
        "series_prior_draw_rate_smoothed_500",
        "series_events_seen_log",
        "avg_player_prior_draw_smoothed_50",
        "median_player_prior_draw_smoothed_50",
        "max_player_prior_draw_smoothed_50",
        "avg_player_prior_games",
        "min_player_prior_games",
        "player_prior_confidence_avg",
        "all_players_can_draw_into_cut",
        "any_player_eliminated_by_draw",
        "all_players_locked_with_draw",
        "count_players_draw_as_good_as_win",
        "count_players_loss_eliminates",
        "draw_preserves_cut_rank_count",
        "win_changes_cut_status_count",
        "same_points_count_in_pod",
        "all_players_same_points",
        "points_range_within_pod",
        "min_points_in_pod",
        "max_points_in_pod",
        "all_players_above_projected_cut_line",
        "all_players_within_one_point_of_cut_line",
        "last_round_cut_fraction",
        "penultimate_round_cut_fraction",
        "round_number_size_bucket",
        "last_round_size_bucket",
        "round_size_cut_bucket_key",
        "round_size_cut_prior_draw_rate_smoothed_100",
        "decisive_win_probability_entropy",
        "max_decisive_win_probability",
        "min_decisive_win_probability",
        "decisive_win_probability_spread",
        "any_repeat_pair",
        "count_repeat_pairs",
        "pod_size_round_number",
        "pod_size_is_last_swiss_round",
        "pod_size_cut_fraction",
        "pod_size_series_prior_draw_rate",
        "series_pod_size_prior_draw_rate_smoothed_100",
        "series_prior_draw_rate_residual",
        "count_players_with_no_history",
        "count_players_with_low_history",
        "all_elos_default",
        "count_default_elos",
        "seat_data_missing",
        "min_draw_secure_rank",
        "max_draw_secure_rank",
        "draw_secure_rank_spread",
        "all_players_draw_rank_within_cut_plus_4",
        "all_players_draw_rank_within_cut_plus_8",
        "bye_fraction",
        "bye_line_points",
        "expected_bye_line_points",
        "count_currently_in_bye",
        "count_draw_secures_bye",
        "count_win_secures_bye",
        "count_must_win_for_bye",
        "count_players_win_only_live",
        "count_players_win_only_live_for_bye",
        "all_players_draw_lock_cut",
        "all_players_draw_lock_bye",
        "min_draw_rank_margin_to_cut",
        "min_draw_rank_margin_to_bye",
        "count_players_draw_makes_cut",
        "count_players_draw_makes_bye",
        "draw_hurts_any_player_cut_status",
        "draw_hurts_any_player_bye_status",
        "draw_hurts_any_player_status",
        "all_players_above_cut_after_draw",
        "all_players_above_bye_after_draw",
        "all_players_above_cut_after_loss",
        "all_players_above_bye_after_loss",
        "pod_has_asymmetric_cut_incentive",
        "pod_has_asymmetric_bye_incentive",
        "pod_has_asymmetric_incentive",
        "draw_vs_win_status_same_count",
        "pairwise_mutual_draw_benefit_count",
        "count_players_draw_as_good_as_win_for_bye",
    ]
    raw_series_features = {"series_prior_draw_rate", "series_events_seen"}
    smoothed_series_features = {
        "series_prior_draw_rate_smoothed_50",
        "series_prior_draw_rate_smoothed_100",
        "series_prior_draw_rate_smoothed_250",
        "series_prior_draw_rate_smoothed_500",
        "series_pod_size_prior_draw_rate_smoothed_100",
        "series_prior_draw_rate_residual",
        "series_events_seen_log",
    }
    player_history_features = {
        "avg_player_prior_draw",
        "median_player_prior_draw",
        "min_player_prior_draw",
        "max_player_prior_draw",
        "prior_draw_std",
        "prior_draw_range",
        "count_high_draw_players",
        "count_high_win_low_draw_players",
        "draw_rate_range_above_threshold",
        "avg_player_prior_win",
        "max_player_prior_win",
        "avg_player_prior_decisive",
        "max_player_prior_decisive",
        "avg_player_prior_draw_smoothed_50",
        "median_player_prior_draw_smoothed_50",
        "max_player_prior_draw_smoothed_50",
        "avg_player_prior_games",
        "min_player_prior_games",
        "player_prior_confidence_avg",
        "count_players_with_no_history",
        "count_players_with_low_history",
        "all_elos_default",
        "count_default_elos",
        "seat_data_missing",
    }
    feature_sets = {
        "full": full_features,
        "projected_cut_only": [
            feature
            for feature in full_features
            if feature
            not in {
                "current_cut_line_points",
                "avg_points_to_current_cut",
                "min_points_to_current_cut",
                "count_locked_for_current_cut",
                "count_dead_for_current_cut",
                "count_draw_safe_for_current_cut",
                "count_must_win_for_current_cut",
                "all_players_draw_safe_for_current_cut",
            }
        ],
        "current_cut_only": [
            feature
            for feature in full_features
            if feature
            not in {
                "expected_cut_line_points",
                "avg_points_to_cut",
                "min_points_to_cut",
                "count_locked_for_cut",
                "count_dead_for_cut",
                "count_live_for_cut",
                "count_draw_safe_for_cut",
                "count_must_win_for_cut",
                "all_players_draw_safe",
            }
        ],
        "no_calendar": [feature for feature in full_features if feature not in {"month", "quarter"}],
        "no_seat": [feature for feature in full_features if feature not in {"seat_highest", "seat_second", "top2_adjacent"}],
        "no_player_history": [feature for feature in full_features if feature not in player_history_features],
        "no_recent_global": [feature for feature in full_features if feature != "global_recent_draw_rate_90d"],
        "no_round_context": [
            feature
            for feature in full_features
            if feature
            not in {
                "swiss_progress",
                "round_number",
                "rounds_remaining",
                "is_last_swiss_round",
                "is_penultimate_swiss_round",
                "last_round_cut_fraction",
                "penultimate_round_cut_fraction",
                "round_number_size_bucket",
                "last_round_size_bucket",
                "round_size_cut_bucket_key",
                "round_size_cut_prior_draw_rate_smoothed_100",
            }
        ],
        "no_series": [feature for feature in full_features if feature not in raw_series_features | smoothed_series_features],
        "smoothed_series_only": [
            feature for feature in full_features if feature not in raw_series_features
        ],
        "raw_series_only": [
            feature for feature in full_features if feature not in smoothed_series_features
        ],
        "smoothed_series_100_only": [
            feature
            for feature in full_features
            if feature not in raw_series_features | smoothed_series_features
        ]
        + ["series_prior_draw_rate_smoothed_100", "series_events_seen_log"],
        "compact": [
            "pod_size",
            "spread",
            "mean_elo",
            "top2_mean_elo",
            "elo_std",
            "high1550",
            "high1700",
            "seat_highest",
            "top2_adjacent",
            "swiss_progress",
            "tournament_size",
            "global_recent_draw_rate_90d",
            "avg_player_prior_draw",
        ],
    }
    v11_direct_incentive_features = {
        "bye_fraction",
        "bye_line_points",
        "expected_bye_line_points",
        "count_currently_in_bye",
        "count_draw_secures_bye",
        "count_win_secures_bye",
        "count_must_win_for_bye",
        "count_players_win_only_live",
        "count_players_win_only_live_for_bye",
        "all_players_draw_lock_cut",
        "all_players_draw_lock_bye",
        "min_draw_rank_margin_to_cut",
        "min_draw_rank_margin_to_bye",
        "count_players_draw_makes_cut",
        "count_players_draw_makes_bye",
        "draw_hurts_any_player_cut_status",
        "draw_hurts_any_player_bye_status",
        "draw_hurts_any_player_status",
        "all_players_above_cut_after_draw",
        "all_players_above_bye_after_draw",
        "all_players_above_cut_after_loss",
        "all_players_above_bye_after_loss",
        "pod_has_asymmetric_cut_incentive",
        "pod_has_asymmetric_bye_incentive",
        "pod_has_asymmetric_incentive",
        "draw_vs_win_status_same_count",
        "pairwise_mutual_draw_benefit_count",
        "count_players_draw_as_good_as_win_for_bye",
    }
    v11b_core_direct_incentive_features = {
        "all_players_draw_lock_cut",
        "all_players_draw_lock_bye",
        "min_draw_rank_margin_to_cut",
        "min_draw_rank_margin_to_bye",
        "count_players_draw_makes_cut",
        "count_players_draw_makes_bye",
        "count_players_win_only_live",
        "count_players_win_only_live_for_bye",
        "count_players_loss_eliminates",
        "draw_vs_win_status_same_count",
        "draw_hurts_any_player_status",
        "all_players_above_cut_after_draw",
        "all_players_above_bye_after_draw",
        "all_players_above_cut_after_loss",
        "all_players_above_bye_after_loss",
        "pod_has_asymmetric_incentive",
        "pairwise_mutual_draw_benefit_count",
    }
    feature_sets["v11b_intentional_core"] = [
        feature
        for feature in feature_sets["projected_cut_only"]
        if feature not in v11_direct_incentive_features or feature in v11b_core_direct_incentive_features
    ]

    base_params = {
        "learning_rate": 0.08,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 250,
        "max_depth": None,
        "l2_regularization": 0.0,
    }
    feature_results = evaluate_feature_sets(folds, feature_sets, half_life=90, base_params=base_params)
    print("Feature pruning results:", flush=True)
    for log_loss, brier, name, features in feature_results:
        print(
            {
                "avg_val_log_loss": log_loss,
                "avg_val_brier": brier,
                "feature_set": name,
                "feature_count": len(features),
            },
            flush=True,
        )
    series_holdout_feature_sets = {
        name: feature_sets[name]
        for name in (
            "full",
            "projected_cut_only",
            "no_series",
            "smoothed_series_only",
            "smoothed_series_100_only",
            "raw_series_only",
            "v11b_intentional_core",
        )
        if name in feature_sets
    }
    series_holdout_results = evaluate_series_holdout_feature_sets(
        development_rows,
        series_holdout_feature_sets,
        fold_count=5,
        half_life=90,
        base_params=base_params,
    )
    print("Series-holdout feature results:", flush=True)
    for row in series_holdout_results:
        print(
            {
                "feature_set": row["feature_set"],
                "avg_series_holdout_log_loss": row["avg_series_holdout_log_loss"],
                "avg_series_holdout_brier": row["avg_series_holdout_brier"],
            },
            flush=True,
        )

    if args.force_feature_set:
        if args.force_feature_set not in feature_sets:
            raise ValueError(f"Unknown --force-feature-set {args.force_feature_set!r}. Options: {sorted(feature_sets)}")
        feature_set_name = args.force_feature_set
        selected_features = feature_sets[feature_set_name]
    else:
        _, _, feature_set_name, selected_features = feature_results[0]
    print(f"Best feature set after pruning: {feature_set_name} {selected_features}", flush=True)

    hyperparameter_results = tune_hgb_holdout(train_rows, validation_rows, selected_features)
    print("Top hyperparameter candidates on holdout validation:", flush=True)
    for log_loss, brier, half_life, params in hyperparameter_results[:10]:
        print({"val_log_loss": log_loss, "val_brier": brier, "half_life": half_life, **params}, flush=True)

    rolling_results = evaluate_finalists_rolling(folds, selected_features, hyperparameter_results[:5])
    print("Rolling-validation finalists:", flush=True)
    for log_loss, brier, half_life, params in rolling_results:
        print({"rolling_val_log_loss": log_loss, "rolling_val_brier": brier, "half_life": half_life, **params}, flush=True)

    _, _, best_half_life, best_params = rolling_results[0]
    selection = ModelSelection(
        feature_set_name=feature_set_name,
        features=selected_features,
        half_life=best_half_life,
        learning_rate=float(best_params["learning_rate"]),
        max_leaf_nodes=int(best_params["max_leaf_nodes"]),
        min_samples_leaf=int(best_params["min_samples_leaf"]),
        max_depth=best_params["max_depth"],
        l2_regularization=float(best_params["l2_regularization"]),
    )
    print(f"Selected final uncalibrated HGB: {asdict(selection)}", flush=True)

    x_train, y_train = make_xy(train_rows, selected_features)
    x_validation, y_validation = make_xy(validation_rows, selected_features)
    x_test, y_test = make_xy(test_rows, selected_features)
    train_weight = np.asarray(
        [recency_weight(row.date, train_rows[-1].date, best_half_life) for row in train_rows],
        dtype=float,
    )
    hgb_model = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **best_params)
    hgb_model.fit(x_train, y_train, sample_weight=train_weight)
    validation_probabilities = hgb_model.predict_proba(x_validation)[:, 1]
    test_probabilities = hgb_model.predict_proba(x_test)[:, 1]
    uncalibrated_log_loss, uncalibrated_brier = score_probs(y_test, test_probabilities)
    print(
        "Uncalibrated holdout:",
        {"test_log_loss": uncalibrated_log_loss, "test_brier": uncalibrated_brier},
        flush=True,
    )

    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic.fit(validation_probabilities, y_validation)
    isotonic_test = isotonic.predict(test_probabilities)
    isotonic_log_loss, isotonic_brier = score_probs(y_test, isotonic_test)
    print(
        "Isotonic calibrated holdout:",
        {"test_log_loss": isotonic_log_loss, "test_brier": isotonic_brier},
        flush=True,
    )

    platt = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    platt.fit(validation_probabilities.reshape(-1, 1), y_validation)
    platt_test = platt.predict_proba(test_probabilities.reshape(-1, 1))[:, 1]
    platt_log_loss, platt_brier = score_probs(y_test, platt_test)
    print(
        "Platt calibrated holdout:",
        {"test_log_loss": platt_log_loss, "test_brier": platt_brier},
        flush=True,
    )

    family_results = compare_tree_families(development_rows, test_rows, selected_features, best_half_life, best_params)
    print("Alternate family results:", flush=True)
    for log_loss, brier, family, params in family_results:
        print(
            {
                "test_log_loss": log_loss,
                "test_brier": brier,
                "family": family,
                "params": {
                    key: params.get(key)
                    for key in (
                        "n_estimators",
                        "min_samples_leaf",
                        "max_features",
                        "learning_rate",
                        "max_leaf_nodes",
                        "l2_regularization",
                    )
                    if key in params
                },
            },
            flush=True,
        )

    development_weight = np.asarray(
        [recency_weight(row.date, development_rows[-1].date, best_half_life) for row in development_rows],
        dtype=float,
    )
    final_hgb = HistGradientBoostingClassifier(loss="log_loss", random_state=0, **best_params)
    x_development, y_development = make_xy(development_rows, selected_features)
    final_hgb.fit(x_development, y_development, sample_weight=development_weight)
    permutation = compute_permutation_importance(final_hgb, x_test, y_test, selected_features)
    print("Top permutation importances:", flush=True)
    for feature, importance in permutation[:15]:
        print({"feature": feature, "importance": importance}, flush=True)

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    calibration_scores = {
        "none": uncalibrated_log_loss,
        "isotonic": isotonic_log_loss,
        "platt": platt_log_loss,
    }
    best_calibration = min(calibration_scores, key=calibration_scores.get)
    artifact = {
        "selection": asdict(selection),
        "model": final_hgb,
        "calibration": best_calibration,
        "calibrator": platt if best_calibration == "platt" else isotonic if best_calibration == "isotonic" else None,
    }
    with artifact_path.open("wb") as handle:
        pickle.dump(artifact, handle)

    report = {
        "selection": asdict(selection),
        "feature_pruning": [
            {
                "avg_val_log_loss": log_loss,
                "avg_val_brier": brier,
                "feature_set": name,
                "feature_count": len(features),
            }
            for log_loss, brier, name, features in feature_results
        ],
        "series_holdout_feature_results": series_holdout_results,
        "hyperparameter_results": [
            {"val_log_loss": log_loss, "val_brier": brier, "half_life": half_life, **params}
            for log_loss, brier, half_life, params in hyperparameter_results[:10]
        ],
        "rolling_results": [
            {"rolling_val_log_loss": log_loss, "rolling_val_brier": brier, "half_life": half_life, **params}
            for log_loss, brier, half_life, params in rolling_results
        ],
        "holdout": {
            "uncalibrated": {"test_log_loss": uncalibrated_log_loss, "test_brier": uncalibrated_brier},
            "isotonic": {"test_log_loss": isotonic_log_loss, "test_brier": isotonic_brier},
            "platt": {"test_log_loss": platt_log_loss, "test_brier": platt_brier},
        },
        "alternate_families": [
            {
                "test_log_loss": log_loss,
                "test_brier": brier,
                "family": family,
                "params": {
                    key: params.get(key)
                    for key in (
                        "n_estimators",
                        "min_samples_leaf",
                        "max_features",
                        "learning_rate",
                        "max_leaf_nodes",
                        "l2_regularization",
                    )
                    if key in params
                },
            }
            for log_loss, brier, family, params in family_results
        ],
        "permutation_importance": [
            {"feature": feature, "importance": importance}
            for feature, importance in permutation[:15]
        ],
        "artifact_path": str(artifact_path),
        "cache_path": str(cache_path),
        "best_calibration": best_calibration,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote artifact to {artifact_path}", flush=True)
    print(f"Wrote report to {report_path}", flush=True)


if __name__ == "__main__":
    main()
