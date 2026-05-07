#!/usr/bin/env python3
"""Core simulation types for pod and tournament Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


ALL_DRAW_FEATURES = [
    "is_swiss",
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
]


@dataclass(slots=True)
class SimPlayer:
    player_id: str
    name: str
    elo: float
    commander_id: str | None = None
    commander_known: bool = False
    commander_elo: float = 1500.0
    topdeck_id: str | None = None
    tiebreak_seed: int = 0


@dataclass(slots=True)
class StandingRow:
    player_id: str
    points: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    pods_played: int = 0
    bye_count: int = 0
    opponents: set[str] = field(default_factory=set)


@dataclass(slots=True)
class Pod:
    round_index: int
    table_number: int
    player_ids: list[str]
    round_name: str | None = None
    seats_by_player: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class PodResult:
    round_index: int
    table_number: int
    player_ids: list[str]
    is_draw: bool
    winner_id: str | None
    win_probabilities: tuple[float, ...]
    draw_probability: float


@dataclass(slots=True)
class TournamentSpec:
    tournament_id: str
    name: str
    start_date: datetime
    swiss_rounds: int
    top_cut: int
    player_count: int
    pod_size: int = 4
    state: str | None = None
    country: str | None = None


@dataclass(slots=True)
class TournamentContext:
    start_date: datetime | None = None
    player_count: int = 0
    series_key: str = "unknown_series"
    state_key: str = ""
    country_key: str = ""
    top_cut: int = 0
    max_rounds: int = 0


@dataclass(slots=True)
class PlayerHistory:
    draw_rate: float = 0.0
    win_rate: float = 0.0
    decisive_rate: float = 0.0


@dataclass(slots=True)
class FeatureContext:
    player_history: dict[str, PlayerHistory] = field(default_factory=dict)
    tournament_pair_meetings: dict[tuple[str, str], int] = field(default_factory=dict)
    global_pair_meetings: dict[tuple[str, str], int] = field(default_factory=dict)
    series_prior_draw_rate: float = 0.0
    series_events_seen: int = 0
    state_prior_draw_rate: float = 0.0
    country_prior_draw_rate: float = 0.0
    global_recent_draw_rate_90d: float = 0.0


@dataclass(slots=True)
class RoundFeatureSnapshot:
    round_number: int
    swiss_progress: float
    rounds_remaining: int
    month: int
    quarter: int
    tournament_size: int
    size_bucket: int
    field_size: int
    cut_fraction: float
    cut_size_bucket: int
    cut_line_percentile: float
    cut_line_points: int
    expected_cut_line_points: float
    max_future_points: int
    bubble_margin: float
    points_by_player: dict[str, int]
    point_percentiles: dict[str, float]
    estimated_omw_by_player: dict[str, float]
    same_points_omw_percentile_by_player: dict[str, float]
    current_rank_by_player: dict[str, int]
    draw_secure_rank_by_player: dict[str, int]
    win_secure_rank_by_player: dict[str, int]


@dataclass(slots=True)
class TournamentState:
    spec: TournamentSpec
    players: dict[str, SimPlayer]
    standings: dict[str, StandingRow]
    completed_pods: list[PodResult] = field(default_factory=list)
    current_round_index: int = 0
    feature_context: FeatureContext = field(default_factory=FeatureContext)
    round_draw_counts: dict[int, int] = field(default_factory=dict)
    round_pod_counts: dict[int, int] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationSummary:
    win_counts: dict[str, int]
    top_cut_counts: dict[str, int]
    expected_points_total: dict[str, float]
    expected_finish_total: dict[str, float]
    round_draw_counts: dict[int, int]
    round_pod_counts: dict[int, int]
    simulations: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "win_probability": {
                player_id: count / self.simulations for player_id, count in self.win_counts.items()
            },
            "top_cut_probability": {
                player_id: count / self.simulations for player_id, count in self.top_cut_counts.items()
            },
            "expected_points": {
                player_id: total / self.simulations for player_id, total in self.expected_points_total.items()
            },
            "expected_finish": {
                player_id: total / self.simulations for player_id, total in self.expected_finish_total.items()
            },
            "round_draw_rate": {
                round_index: (
                    self.round_draw_counts.get(round_index, 0) / self.round_pod_counts.get(round_index, 1)
                )
                for round_index in self.round_pod_counts
            },
            "simulations": self.simulations,
        }
