#!/usr/bin/env python3
"""Repair participant result rows that disagree with the game-level outcome."""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests


def load_env() -> None:
    for env_path in (
        Path("packages/backend/.env"),
        Path(".env"),
        Path(__file__).resolve().parents[1] / ".env",
    ):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


class RestClient:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def request(
        self,
        method: str,
        table: str,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        endpoint = f"{self.url}/rest/v1/{table}"
        request_headers = headers or self.headers
        for attempt in range(5):
            try:
                response = requests.request(
                    method,
                    endpoint,
                    headers=request_headers,
                    timeout=90,
                    **kwargs,
                )
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException:
                if attempt >= 4:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable retry state")

    def get_pages(self, table: str, params: dict[str, str], page_size: int = 1000):
        offset = 0
        while True:
            headers = self.headers.copy()
            headers["Range"] = f"{offset}-{offset + page_size - 1}"
            response = self.request("GET", table, headers=headers, params=params)
            rows = response.json()
            if not rows:
                break
            yield rows
            if len(rows) < page_size:
                break
            offset += page_size

    def patch_participant(self, participant_id: str, result: str, points: int) -> None:
        self.request(
            "PATCH",
            "game_participants",
            params={"id": f"eq.{participant_id}"},
            json={"result": result, "points_earned": points},
        )

    def patch_participant_group(self, participant_ids: list[str], result: str, points: int) -> int:
        response = self.request(
            "PATCH",
            "game_participants",
            params={"id": f"in.({','.join(participant_ids)})"},
            json={"result": result, "points_earned": points},
        )
        data = response.json()
        return len(data) if isinstance(data, list) else 0


def expected_for_participant(game: dict[str, Any], participant: dict[str, Any]) -> tuple[str, int] | None:
    entry = participant.get("tournament_entries") or {}
    player_id = entry.get("player_id")
    if game.get("is_draw"):
        return ("draw", 1)
    winner_id = game.get("winner_id")
    if winner_id and player_id:
        return ("win", 5) if player_id == winner_id else ("loss", 0)
    return None


def scan_games(client: RestClient, *, include_draws: bool) -> list[dict[str, Any]]:
    filters = [
        {
            "winner_id": "not.is.null",
            "is_draw": "eq.false",
            "order": "tournament_id.asc,round_number.asc,table_number.asc",
        }
    ]
    if include_draws:
        filters.append(
            {
                "winner_id": "is.null",
                "is_draw": "eq.true",
                "order": "tournament_id.asc,round_number.asc,table_number.asc",
            }
        )

    mismatches: list[dict[str, Any]] = []
    scanned = 0
    select = (
        "id,tournament_id,round_number,round_name,table_number,is_draw,winner_id,"
        "tournaments(topdeck_tid,name),"
        "game_participants(id,result,points_earned,tournament_entries(player_id))"
    )
    for params in filters:
        params = {"select": select, **params}
        for page in client.get_pages("games", params):
            scanned += len(page)
            if scanned % 25000 == 0:
                print(f"scanned_games={scanned}", flush=True)
            for game in page:
                participant_updates = []
                for participant in game.get("game_participants") or []:
                    expected = expected_for_participant(game, participant)
                    if expected is None:
                        continue
                    expected_result, expected_points = expected
                    if (
                        participant.get("result") != expected_result
                        or participant.get("points_earned") != expected_points
                    ):
                        participant_updates.append(
                            {
                                "participant_id": participant["id"],
                                "old_result": participant.get("result"),
                                "old_points": participant.get("points_earned"),
                                "new_result": expected_result,
                                "new_points": expected_points,
                            }
                        )
                if participant_updates:
                    mismatches.append({"game": game, "updates": participant_updates})

    print(f"scanned_games={scanned}", flush=True)
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-draws", action="store_true")
    args = parser.parse_args()

    load_env()
    client = RestClient(require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY"))
    mismatches = scan_games(client, include_draws=args.include_draws)

    tournament_counts: Counter[str] = Counter()
    participant_update_count = 0
    for mismatch in mismatches:
        game = mismatch["game"]
        tournament = game.get("tournaments") or {}
        label = f"{tournament.get('topdeck_tid') or game['tournament_id']} | {tournament.get('name') or ''}"
        tournament_counts[label] += 1
        participant_update_count += len(mismatch["updates"])

    print(f"mismatch_games={len(mismatches)}")
    print(f"participant_updates={participant_update_count}")
    for label, count in tournament_counts.most_common(25):
        print(f"{count}\t{label}")
    if len(tournament_counts) > 25:
        print(f"... {len(tournament_counts) - 25} more tournaments")

    if not args.apply:
        print("dry_run=true")
        return 0

    update_groups: dict[tuple[str, int], list[str]] = {}
    for mismatch in mismatches:
        for update in mismatch["updates"]:
            key = (update["new_result"], update["new_points"])
            update_groups.setdefault(key, []).append(update["participant_id"])
    applied = 0
    for (result, points), participant_ids in sorted(update_groups.items()):
        for start in range(0, len(participant_ids), 250):
            applied += client.patch_participant_group(
                participant_ids[start : start + 250],
                result,
                points,
            )
            print(f"applied_participant_updates={applied}", flush=True)
    print(f"applied_participant_updates={applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
