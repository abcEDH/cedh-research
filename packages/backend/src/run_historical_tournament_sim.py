#!/usr/bin/env python3
"""Run Monte Carlo simulation for a historical tournament from Supabase."""

from __future__ import annotations

import argparse
import json
import os
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from ingest import SupabaseClient, load_local_env
from sim_engine import run_monte_carlo
from sim_models import load_draw_model_artifact
from sim_types import FeatureContext, PlayerHistory, SimPlayer, TournamentSpec

DEFAULT_DRAW_MODEL_PATH = Path("/tmp/cedh_draw_model_artifact_v4.pkl")
def fetch_all(
    client: SupabaseClient,
    table: str,
    params: dict[str, str],
    *,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = client.select(table, {**params, "limit": str(limit), "offset": str(offset)}, max_retries=8)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return rows


def batched(values: list[str], batch_size: int) -> list[list[str]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


def in_filter(values: list[str]) -> str:
    escaped = [value.replace('"', '\\"') for value in values]
    return "(" + ",".join(f'"{value}"' for value in escaped) + ")"


def fetch_tournament(client: SupabaseClient, tournament_id: str) -> dict[str, Any]:
    rows = client.select(
        "tournaments",
        {
            "select": "id,name,start_date,player_count,top_cut,state,country",
            "id": f"eq.{tournament_id}",
            "limit": "1",
        },
    )
    if not rows:
        raise RuntimeError(f"Tournament not found: {tournament_id}")
    return rows[0]


def fetch_entries(client: SupabaseClient, tournament_id: str) -> list[dict[str, Any]]:
    return fetch_all(
        client,
        "tournament_entries",
        {
            "select": "player_id,commander_id,final_standing,made_top_cut,players(name,topdeck_id),commanders(name)",
            "tournament_id": f"eq.{tournament_id}",
        },
    )


def derive_top_cut_player_ids(entries: list[dict[str, Any]], top_cut: int) -> set[str]:
    if top_cut <= 0:
        return set()
    top_cut_players: set[str] = set()
    for row in entries:
        player_id = row.get("player_id")
        final_standing = row.get("final_standing")
        if not player_id or final_standing is None:
            continue
        try:
            if int(final_standing) <= top_cut:
                top_cut_players.add(str(player_id))
        except (TypeError, ValueError):
            continue
    return top_cut_players


def infer_swiss_rounds(client: SupabaseClient, tournament_id: str) -> int:
    rows = fetch_all(
        client,
        "global_elo_game_results",
        {
            "select": "round_number",
            "tournament_id": f"eq.{tournament_id}",
        },
    )
    round_numbers = [int(row["round_number"]) for row in rows if row.get("round_number") is not None]
    if not round_numbers:
        raise RuntimeError(f"No swiss rounds found for tournament {tournament_id}")
    return max(round_numbers)


def fetch_pre_tournament_elos(
    client: SupabaseClient,
    player_ids: list[str],
    start_date: str,
) -> dict[str, float]:
    ratings: dict[str, tuple[str, float]] = {}
    for batch in batched(player_ids, 40):
        rows = fetch_all(
            client,
            "global_elo_game_events",
            {
                "select": "player_id,game_date,rating_after",
                "region_type": "eq.global",
                "region_key": "eq.ALL",
                "game_date": f"lt.{start_date}",
                "player_id": f"in.{in_filter(batch)}",
                "order": "game_date.desc",
            },
        )
        for row in rows:
            player_id = row.get("player_id")
            game_date = row.get("game_date")
            rating_after = row.get("rating_after")
            if not player_id or game_date is None or rating_after is None:
                continue
            if player_id not in ratings:
                ratings[player_id] = (str(game_date), float(rating_after))
    return {player_id: rating for player_id, (_, rating) in ratings.items()}


def build_feature_context(
    client: SupabaseClient,
    player_ids: list[str],
    start_date: str,
) -> FeatureContext:
    player_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    prior_games: dict[str, list[str]] = defaultdict(list)
    for batch in batched(player_ids, 40):
        rows = fetch_all(
            client,
            "global_elo_game_results",
            {
                "select": "game_id,player_id,result",
                "player_id": f"in.{in_filter(batch)}",
                "start_date": f"lt.{start_date}",
            },
        )
        for row in rows:
            player_id = row.get("player_id")
            result = str(row.get("result") or "")
            game_id = row.get("game_id")
            if not player_id or not game_id:
                continue
            stats = player_stats[player_id]
            stats[1] += 1
            if result == "draw":
                stats[0] += 1
            if result == "win":
                stats[2] += 1
            if result != "draw":
                stats[3] += 1
            prior_games[str(game_id)].append(player_id)

    tournament_pair_meetings: dict[tuple[str, str], int] = {}
    global_pair_meetings: dict[tuple[str, str], int] = defaultdict(int)
    for players in prior_games.values():
        unique_players = sorted(set(players))
        for index, player_id in enumerate(unique_players):
            for opponent_id in unique_players[index + 1 :]:
                pair = (player_id, opponent_id)
                global_pair_meetings[pair] += 1

    history = {}
    for player_id in player_ids:
        draws, total, wins, decisive = player_stats[player_id]
        history[player_id] = PlayerHistory(
            draw_rate=(draws / total) if total else 0.0,
            win_rate=(wins / total) if total else 0.0,
            decisive_rate=(decisive / total) if total else 0.0,
        )

    return FeatureContext(
        player_history=history,
        tournament_pair_meetings=tournament_pair_meetings,
        global_pair_meetings=dict(global_pair_meetings),
        series_prior_draw_rate=0.0,
        series_events_seen=0,
        state_prior_draw_rate=0.0,
        country_prior_draw_rate=0.0,
        global_recent_draw_rate_90d=0.0,
    )


def build_spec_and_players(client: SupabaseClient, tournament_id: str) -> tuple[TournamentSpec, list[SimPlayer], list[dict[str, Any]], FeatureContext]:
    tournament = fetch_tournament(client, tournament_id)
    entries = fetch_entries(client, tournament_id)
    swiss_rounds = infer_swiss_rounds(client, tournament_id)
    player_ids = [str(row["player_id"]) for row in entries if row.get("player_id")]
    pre_elos = fetch_pre_tournament_elos(client, player_ids, str(tournament["start_date"]))
    feature_context = build_feature_context(client, player_ids, str(tournament["start_date"]))

    sortable_entries = []
    for row in entries:
        player_id = row.get("player_id")
        player = row.get("players") or {}
        if not player_id:
            continue
        sortable_entries.append(
            (
                str(player_id),
                str(player.get("name") or player_id),
                player.get("topdeck_id"),
                float(pre_elos.get(str(player_id), 1500.0)),
            )
        )

    seed_source = f"historical:{tournament_id}"
    seeded_rng = random.Random(seed_source)
    seeded_rng.shuffle(sortable_entries)
    players = []
    for tiebreak_seed, (player_id, name, topdeck_id, elo) in enumerate(sortable_entries, start=1):
        players.append(
            SimPlayer(
                player_id=player_id,
                name=name,
                elo=elo,
                topdeck_id=topdeck_id,
                tiebreak_seed=tiebreak_seed,
            )
        )

    spec = TournamentSpec(
        tournament_id=str(tournament["id"]),
        name=str(tournament["name"]),
        start_date=datetime.fromisoformat(str(tournament["start_date"]).replace("Z", "+00:00")),
        swiss_rounds=swiss_rounds,
        top_cut=int(tournament.get("top_cut") or 0),
        player_count=int(tournament.get("player_count") or len(players)),
        state=tournament.get("state"),
        country=tournament.get("country"),
    )
    return spec, players, entries, feature_context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tournament-id", required=True)
    parser.add_argument("--draw-model-path", default=str(DEFAULT_DRAW_MODEL_PATH))
    parser.add_argument("--simulations", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    load_local_env()
    client = SupabaseClient(url=os.environ["SUPABASE_URL"], service_key=os.environ["SUPABASE_SERVICE_KEY"])
    spec, players, entries, feature_context = build_spec_and_players(client, args.tournament_id)
    draw_model = load_draw_model_artifact(args.draw_model_path)
    summary = run_monte_carlo(
        spec,
        players,
        draw_model,
        simulations=args.simulations,
        seed=args.seed,
        feature_context=feature_context,
        workers=args.workers,
    )

    actual_top_cut = derive_top_cut_player_ids(entries, spec.top_cut)
    actual_winner = next((str(row["player_id"]) for row in entries if row.get("final_standing") == 1), None)
    top_win = sorted(summary.to_dict()["win_probability"].items(), key=lambda item: item[1], reverse=True)[:10]
    top_cut_prob = sorted(summary.to_dict()["top_cut_probability"].items(), key=lambda item: item[1], reverse=True)[:10]
    player_name_by_id = {player.player_id: player.name for player in players}

    output = {
        "tournament": {
            "id": spec.tournament_id,
            "name": spec.name,
            "player_count": spec.player_count,
            "swiss_rounds": spec.swiss_rounds,
            "top_cut": spec.top_cut,
        },
        "simulations": args.simulations,
        "actual_winner": {"player_id": actual_winner, "name": player_name_by_id.get(actual_winner or "", actual_winner)},
        "actual_top_cut_count": len(actual_top_cut),
        "top_win_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "win_probability": probability}
            for player_id, probability in top_win
        ],
        "top_top_cut_probabilities": [
            {"player_id": player_id, "name": player_name_by_id.get(player_id, player_id), "top_cut_probability": probability}
            for player_id, probability in top_cut_prob
        ],
        "round_draw_rate": summary.to_dict()["round_draw_rate"],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
