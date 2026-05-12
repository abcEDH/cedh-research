"""Shared tournament simulation runner and output formatting."""

from __future__ import annotations

from typing import Any

from sim_engine import run_monte_carlo_from_state
from sim_models import LoadedDrawModel
from sim_types import Pod, TournamentState

DEFAULT_ADVANCEMENT_SIZES = (64, 40, 16, 10, 4)


def run_simulation_from_state(
    state: TournamentState,
    draw_model: LoadedDrawModel,
    *,
    simulations: int,
    seed: int,
    workers: int | None,
    start_round_index: int | None = None,
    locked_round_pods: list[Pod] | None = None,
    requested_advancement_sizes: tuple[int, ...] = DEFAULT_ADVANCEMENT_SIZES,
    collect_detailed_metrics: bool = True,
    collect_player_metrics: bool = True,
) -> dict[str, Any]:
    return run_monte_carlo_from_state(
        state,
        draw_model,
        simulations=simulations,
        seed=seed,
        workers=workers,
        start_round_index=start_round_index,
        locked_round_pods=locked_round_pods,
        requested_advancement_sizes=requested_advancement_sizes,
        collect_detailed_metrics=collect_detailed_metrics,
        collect_player_metrics=collect_player_metrics,
    ).to_dict()


def top_probability_rows(
    probabilities: dict[str, float],
    player_name_by_id: dict[str, str],
    probability_key: str,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    return [
        {
            "player_id": player_id,
            "name": player_name_by_id.get(player_id, player_id),
            probability_key: probabilities.get(player_id, 0.0),
        }
        for player_id in sorted(
            player_name_by_id,
            key=lambda player_id: probabilities.get(player_id, 0.0),
            reverse=True,
        )[:limit]
    ]


def build_common_output(
    *,
    summary: dict[str, Any],
    state: TournamentState,
    player_name_by_id: dict[str, str],
    active_player_count: int,
    historical_point_requirements: dict[str, Any] | None = None,
    current_state: dict[str, Any] | None = None,
    actual_winner_id: str | None = None,
    actual_top_cut_count: int | None = None,
    top_limit: int = 20,
) -> dict[str, Any]:
    advancement_probability = summary.get("advancement_probability", {})
    point_requirements = dict(summary.get("point_requirements", {}))
    if historical_point_requirements is not None:
        point_requirements["historical_baseline"] = historical_point_requirements

    output: dict[str, Any] = {
        "tournament": {
            "id": state.spec.tournament_id,
            "name": state.spec.name,
            "player_count": state.spec.player_count,
            "active_player_count": active_player_count,
            "swiss_rounds": state.spec.swiss_rounds,
            "top_cut": state.spec.top_cut,
        },
        "point_requirements": point_requirements,
        "top_win_probabilities": top_probability_rows(
            summary.get("win_probability", {}),
            player_name_by_id,
            "win_probability",
            limit=top_limit,
        ),
        "top_top_cut_probabilities": top_probability_rows(
            summary.get("top_cut_probability", {}),
            player_name_by_id,
            "top_cut_probability",
            limit=top_limit,
        ),
        "round_draw_rate": summary.get("round_draw_rate", {}),
        "simulations": summary["simulations"],
    }

    for cut_size in DEFAULT_ADVANCEMENT_SIZES:
        output[f"top_top{cut_size}_probabilities"] = top_probability_rows(
            advancement_probability.get(cut_size, {}),
            player_name_by_id,
            f"top{cut_size}_probability",
            limit=top_limit,
        )

    if current_state is not None:
        output["current_state"] = current_state
    if actual_winner_id is not None:
        output["actual_winner"] = {
            "player_id": actual_winner_id,
            "name": player_name_by_id.get(actual_winner_id, actual_winner_id),
        }
    if actual_top_cut_count is not None:
        output["actual_top_cut_count"] = actual_top_cut_count
    return output
