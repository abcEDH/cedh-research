"""Batch and streaming execution of the same live tournament model."""

from __future__ import annotations

import json
import os
import random
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Any

from sim_engine import (
    _merge_summaries,
    _run_state_monte_carlo_batch,
    build_tournament_context,
    clone_state,
    resolve_bracket_probabilities,
    simulate_swiss,
)
from sim_models import (
    LoadedCandidateWinnerModel,
    LoadedDrawModel,
    build_round_snapshot,
    predict_pod_outcome_probabilities,
)
from sim_pairings import select_top_cut, sort_standings_rows, topdeck_bye_rank
from sim_types import Pod
from tournament_sim_runner import (
    build_common_output,
)

STREAM_INITIAL_EMIT_SIMULATIONS = 5
STREAM_EMIT_SIMULATION_INTERVAL = 5


def run_live_monte_carlo(
    state,
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None = None,
    *,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    exact_top_cut: bool,
    max_exact_cut_size: int,
    requested_advancement_sizes: tuple[int, ...],
) -> dict[str, Any]:
    context = build_tournament_context(state.spec)
    locked_round_draw_probabilities = None
    locked_round_win_probabilities = None
    if locked_round_pods:
        round_snapshot = build_round_snapshot(state, context, start_round_index + 1)
        locked_round_draw_probabilities, locked_round_win_probabilities = predict_pod_outcome_probabilities(
            locked_round_pods,
            state,
            context,
            draw_model,
            round_snapshot,
            winner_model,
        )

    win_probability_totals: dict[str, float] = defaultdict(float)
    top_cut_counts: dict[str, float] = defaultdict(float)
    advancement_totals: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    expected_points: dict[str, float] = defaultdict(float)
    expected_finish: dict[str, float] = defaultdict(float)
    top_cut_line_point_counts: dict[int, int] = defaultdict(int)
    bye_line_point_counts: dict[int, int] = defaultdict(int)

    for simulation_index in range(simulations):
        simulation_state = clone_state(state)
        rng = random.Random(seed + simulation_index)
        simulate_swiss(
            simulation_state,
            rng,
            draw_model,
            context,
            winner_model,
            start_round_index=start_round_index,
            locked_round_pods=locked_round_pods,
            locked_round_draw_probabilities=locked_round_draw_probabilities,
            locked_round_win_probabilities=locked_round_win_probabilities,
        )
        top_cut = select_top_cut(simulation_state, rng=rng) if simulation_state.spec.top_cut > 0 else []
        for player_id in top_cut:
            top_cut_counts[player_id] += 1.0

        if top_cut:
            if exact_top_cut:
                winner_probabilities, advancement_probabilities = resolve_bracket_probabilities(
                    top_cut,
                    simulation_state,
                    rng,
                    draw_model,
                    context,
                    winner_model,
                    exact_cut_sizes=tuple(cut_size for cut_size in (16, 10, 4) if cut_size <= max_exact_cut_size),
                )
                for player_id, probability in winner_probabilities.items():
                    win_probability_totals[player_id] += probability
                for cut_size in requested_advancement_sizes:
                    for player_id, probability in advancement_probabilities.get(cut_size, {}).items():
                        advancement_totals[cut_size][player_id] += probability
            else:
                from sim_engine import simulate_bracket_winner

                winner_id, advancement_by_size = simulate_bracket_winner(
                    top_cut,
                    simulation_state,
                    rng,
                    draw_model,
                    context,
                    winner_model,
                )
                win_probability_totals[winner_id] += 1.0
                for cut_size in requested_advancement_sizes:
                    for player_id in advancement_by_size.get(cut_size, []):
                        advancement_totals[cut_size][player_id] += 1.0

        ranked = sort_standings_rows(simulation_state)
        if 0 < simulation_state.spec.top_cut <= len(ranked):
            top_cut_line_point_counts[ranked[simulation_state.spec.top_cut - 1].points] += 1
        bye_rank = topdeck_bye_rank(simulation_state.spec.top_cut)
        if bye_rank is not None and bye_rank <= len(ranked):
            bye_line_point_counts[ranked[bye_rank - 1].points] += 1
        for finish_index, standing in enumerate(ranked, start=1):
            expected_points[standing.player_id] += standing.points
            expected_finish[standing.player_id] += finish_index

    return {
        "win_probability": {
            player_id: probability / simulations for player_id, probability in win_probability_totals.items()
        },
        "top_cut_probability": {player_id: count / simulations for player_id, count in top_cut_counts.items()},
        "advancement_probability": {
            cut_size: {player_id: probability / simulations for player_id, probability in player_probabilities.items()}
            for cut_size, player_probabilities in advancement_totals.items()
        },
        "expected_points": {player_id: total / simulations for player_id, total in expected_points.items()},
        "expected_finish": {player_id: total / simulations for player_id, total in expected_finish.items()},
        "point_requirements": {
            "top_cut": [
                {"points": points, "probability": count / simulations, "count": count}
                for points, count in sorted(top_cut_line_point_counts.items())
            ],
            "bye": [
                {"points": points, "probability": count / simulations, "count": count}
                for points, count in sorted(bye_line_point_counts.items())
            ],
        },
        "simulations": simulations,
        "winner_method": "exact_top_cut" if exact_top_cut else "sampled_top_cut",
    }


def run_live_monte_carlo_stream(
    state,
    draw_model: LoadedDrawModel,
    winner_model: LoadedCandidateWinnerModel | None = None,
    *,
    simulations: int,
    seed: int,
    start_round_index: int,
    locked_round_pods: list[Pod] | None,
    max_exact_cut_size: int,
    requested_advancement_sizes: tuple[int, ...],
    stream_interval_seconds: float,
    stream_batch_size: int,
    player_name_by_id: dict[str, str],
    active_player_count: int,
    historical_point_requirements: dict[str, Any] | None,
    current_state: dict[str, Any],
    workers: int | None,
    top_limit: int = 20,
    stream_duration_seconds: float | None = None,
) -> None:
    context = build_tournament_context(state.spec)
    locked_round_draw_probabilities = None
    locked_round_win_probabilities = None
    if locked_round_pods:
        round_snapshot = build_round_snapshot(state, context, start_round_index + 1)
        locked_round_draw_probabilities, locked_round_win_probabilities = predict_pod_outcome_probabilities(
            locked_round_pods,
            state,
            context,
            draw_model,
            round_snapshot,
            winner_model,
        )

    active_pods = []
    for pod in locked_round_pods or []:
        pod_key = (pod.round_index, pod.table_number)
        draw_probability = (locked_round_draw_probabilities or {}).get(pod_key, 0.0)
        decisive_win_probabilities = (locked_round_win_probabilities or {}).get(pod_key, ())
        active_pods.append(
            {
                "round_number": pod.round_index + 1,
                "table_number": pod.table_number,
                "draw_probability": draw_probability,
                "players": [
                    {
                        "player_id": player_id,
                        "name": player_name_by_id.get(player_id, state.players[player_id].name),
                        "win_probability": (1.0 - draw_probability) * decisive_probability,
                        "decisive_win_probability": decisive_probability,
                        "seat": pod.seats_by_player.get(player_id),
                    }
                    for player_id, decisive_probability in zip(
                        pod.player_ids,
                        decisive_win_probabilities,
                        strict=False,
                    )
                ],
            }
        )

    started_at = time.monotonic()
    deadline = (
        started_at + stream_duration_seconds
        if stream_duration_seconds is not None and stream_duration_seconds > 0
        else None
    )

    def time_budget_exhausted() -> bool:
        return deadline is not None and time.monotonic() >= deadline

    def snapshot(summary, *, force_complete: bool = False) -> dict[str, Any]:
        completed = summary.simulations
        winner_method = "hybrid_exact_top16_top10_top4"
        elapsed_seconds = max(0.0, time.monotonic() - started_at)
        simulations_per_second = completed / elapsed_seconds if elapsed_seconds > 0 else 0.0
        duration_progress = (
            min(elapsed_seconds / stream_duration_seconds, 1.0)
            if stream_duration_seconds is not None and stream_duration_seconds > 0
            else None
        )
        status = "complete" if force_complete or completed >= simulations else "running"
        output = {
            "status": status,
            "completed": completed,
            "total": simulations,
            "simulations_per_second": simulations_per_second,
            "progress_percent": (duration_progress * 100) if duration_progress is not None else None,
            **build_common_output(
                summary={**summary.to_dict(), "winner_method": winner_method},
                state=state,
                player_name_by_id=player_name_by_id,
                active_player_count=active_player_count,
                historical_point_requirements=historical_point_requirements,
                current_state=current_state,
                top_limit=top_limit,
            ),
        }
        if active_pods:
            output["active_pods"] = active_pods
        completed_pods = current_state.get("completed_current_round_pods", [])
        if completed_pods:
            output["completed_pods"] = completed_pods
        for unused_key in ("current_state", "round_draw_rate", "tournament"):
            output.pop(unused_key, None)
        return output

    effective_stream_batch_size = max(1, stream_batch_size)
    assigned = 0

    def next_batch_spec(initial: bool = False) -> tuple[int, int] | None:
        nonlocal assigned
        if assigned >= simulations or time_budget_exhausted():
            return None
        batch_size = min(
            STREAM_INITIAL_EMIT_SIMULATIONS if initial else effective_stream_batch_size,
            simulations - assigned,
        )
        batch_seed = seed + assigned
        assigned += batch_size
        return batch_size, batch_seed

    effective_workers = workers if workers is not None else max(1, min(4, os.cpu_count() or 1))
    accumulated = []
    initial_batch = next_batch_spec(initial=True)
    if initial_batch:
        batch_size, batch_seed = initial_batch
        accumulated.append(
            _run_state_monte_carlo_batch(
                state,
                draw_model,
                winner_model,
                simulations=batch_size,
                seed=batch_seed,
                start_round_index=start_round_index,
                locked_round_pods=locked_round_pods,
                locked_round_draw_probabilities=locked_round_draw_probabilities,
                locked_round_win_probabilities=locked_round_win_probabilities,
                requested_advancement_sizes=requested_advancement_sizes,
                collect_detailed_metrics=True,
                collect_player_metrics=False,
            )
        )
        print(json.dumps(snapshot(_merge_summaries(accumulated)), separators=(",", ":")), flush=True)

    if effective_workers <= 1:
        while (batch_spec := next_batch_spec()) is not None:
            batch_size, batch_seed = batch_spec
            accumulated.append(
                _run_state_monte_carlo_batch(
                    state,
                    draw_model,
                    winner_model,
                    simulations=batch_size,
                    seed=batch_seed,
                    start_round_index=start_round_index,
                    locked_round_pods=locked_round_pods,
                    locked_round_draw_probabilities=locked_round_draw_probabilities,
                    locked_round_win_probabilities=locked_round_win_probabilities,
                    requested_advancement_sizes=requested_advancement_sizes,
                    collect_detailed_metrics=True,
                    collect_player_metrics=False,
                )
            )
            summary = _merge_summaries(accumulated)
            print(
                json.dumps(snapshot(summary, force_complete=time_budget_exhausted()), separators=(",", ":")), flush=True
            )
            if time_budget_exhausted():
                break
        return

    with ProcessPoolExecutor(max_workers=effective_workers) as executor:
        futures = {}
        final_summary = _merge_summaries(accumulated) if accumulated else None
        final_snapshot_emitted = False

        def submit_next_batch() -> None:
            batch_spec = next_batch_spec()
            if batch_spec is None:
                return
            batch_size, batch_seed = batch_spec
            future = executor.submit(
                _run_state_monte_carlo_batch,
                state,
                draw_model,
                winner_model,
                batch_size,
                batch_seed,
                start_round_index,
                locked_round_pods,
                locked_round_draw_probabilities,
                locked_round_win_probabilities,
                requested_advancement_sizes,
                True,
                False,
            )
            futures[future] = None

        for _ in range(effective_workers):
            submit_next_batch()

        while futures:
            timeout = None
            if deadline is not None:
                timeout = max(0.0, deadline - time.monotonic())
            done, _ = wait(list(futures), timeout=timeout, return_when=FIRST_COMPLETED)
            if not done and time_budget_exhausted():
                for pending in futures:
                    pending.cancel()
                if final_summary is not None and not final_snapshot_emitted:
                    print(json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True)
                return
            for future in done:
                futures.pop(future, None)
                accumulated.append(future.result())
                summary = _merge_summaries(accumulated)
                final_summary = summary
                force_complete = time_budget_exhausted()
                print(json.dumps(snapshot(summary, force_complete=force_complete), separators=(",", ":")), flush=True)
                final_snapshot_emitted = force_complete or summary.simulations >= simulations
                if summary.simulations >= simulations or time_budget_exhausted():
                    for pending in futures:
                        pending.cancel()
                    if time_budget_exhausted() and final_summary is not None and not final_snapshot_emitted:
                        print(
                            json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True
                        )
                    return
                submit_next_batch()
                break
        if time_budget_exhausted() and final_summary is not None and not final_snapshot_emitted:
            print(json.dumps(snapshot(final_summary, force_complete=True), separators=(",", ":")), flush=True)
