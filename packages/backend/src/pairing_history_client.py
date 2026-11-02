"""Completed historical Swiss rounds and conservative duplicate validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from run_historical_tournament_from_round_sim import fetch_round_rows as fetch_raw_round_rows
from sim_types import Pod, PodResult, TournamentState
from supabase import Client
from supabase_client import fetch_all


@dataclass(frozen=True)
class HistoricalRound:
    pods: list[Pod]
    results: list[PodResult]
    byes: list[str]


def fetch_round_rows(client: Client, tournament_id: str) -> list[dict[str, Any]]:
    games = fetch_all(
        client,
        "games",
        columns="id,status,round_number",
        filters=[("tournament_id", "eq", tournament_id)],
        order=("id", False),
    )
    unfinished_rounds = {
        row.get("round_number")
        for row in games
        if str(row.get("status") or "completed").lower() not in {"completed", "complete", "done"}
    }
    completed_ids = {str(row["id"]) for row in games if row.get("round_number") not in unfinished_rounds}
    return [row for row in fetch_raw_round_rows(client, tournament_id) if str(row.get("game_id")) in completed_ids]


def set_round_eligibility(state: TournamentState, historical_round: HistoricalRound) -> None:
    eligible = {pid for pod in historical_round.pods for pid in pod.player_ids} | set(historical_round.byes)
    missing = eligible - set(state.standings)
    if missing:
        raise ValueError(f"Historical players missing from simulation state: {sorted(missing)}")
    state.eligible_player_ids = eligible


def build_historical_rounds(
    round_rows: list[dict[str, Any]],
    seat_map: dict[tuple[str, str], int],
) -> dict[int, HistoricalRound]:
    grouped: dict[int, dict[tuple[str, int], list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in round_rows:
        round_number = row.get("round_number")
        table_number = row.get("table_number")
        game_id = row.get("game_id")
        if round_number is None or table_number is None or not game_id:
            continue
        grouped[int(round_number)][(str(game_id), int(table_number))].append(row)

    rounds: dict[int, HistoricalRound] = {}
    for round_number, tables in grouped.items():
        pods: list[Pod] = []
        results: list[PodResult] = []
        byes: list[str] = []
        ordered_tables = sorted(tables.items(), key=lambda item: (item[1][0].get("table_number") or 0, item[0][0]))
        seen_signatures = set()
        seen_tables = set()
        seen_players = set()
        for table_index, ((game_id, table_number), rows) in enumerate(ordered_tables, start=1):
            by_player = {}
            for row in rows:
                if not row.get("player_id"):
                    raise ValueError(f"Missing player in game {game_id}")
                pid = str(row["player_id"])
                if pid in by_player and by_player[pid] != row:
                    raise ValueError(f"Conflicting participant rows in game {game_id}")
                by_player[pid] = row
            rows = list(by_player.values())
            if any(
                str(row.get("status") or "completed").lower() not in {"complete", "completed", "done"} for row in rows
            ):
                raise ValueError(f"Unfinished game {game_id} in historical round")
            signature = (
                table_number,
                tuple(
                    sorted(
                        (
                            str(row["player_id"]),
                            str(row.get("result") or "").lower(),
                            seat_map.get((game_id, str(row["entry_id"])), seat),
                        )
                        for seat, row in enumerate(rows, start=1)
                    )
                ),
            )
            if signature in seen_signatures:
                continue
            player_ids = list(by_player)
            if table_number in seen_tables or seen_players.intersection(player_ids):
                raise ValueError(f"Conflicting tables or repeated player in round {round_number}")
            seen_signatures.add(signature)
            seen_tables.add(table_number)
            seen_players.update(player_ids)
            result_values = {str(row.get("result") or "").lower() for row in rows}
            if len(player_ids) == 1 and "bye" in result_values:
                byes.append(player_ids[0])
                continue
            if len(player_ids) < 2:
                continue
            seats_by_player = {
                str(row["player_id"]): seat_map.get((game_id, str(row["entry_id"])), seat)
                for seat, row in enumerate(rows, start=1)
                if row.get("player_id")
            }
            pod = Pod(
                round_index=round_number - 1,
                table_number=int(table_number or table_index),
                player_ids=player_ids,
                round_name=f"Round {round_number}",
                seats_by_player=seats_by_player,
            )
            winner_ids = [str(row["player_id"]) for row in rows if str(row.get("result") or "").lower() == "win"]
            is_draw = result_values == {"draw"}
            if not is_draw and (len(winner_ids) != 1 or not result_values <= {"win", "loss"}):
                raise ValueError(f"Incomplete or conflicting results in game {game_id}")
            pods.append(pod)
            results.append(
                PodResult(
                    round_index=round_number - 1,
                    table_number=pod.table_number,
                    player_ids=player_ids,
                    is_draw=is_draw,
                    winner_id=None if is_draw else (winner_ids[0] if winner_ids else None),
                    win_probabilities=(),
                    draw_probability=0.0,
                )
            )
        rounds[round_number] = HistoricalRound(pods=pods, results=results, byes=byes)
    return rounds
