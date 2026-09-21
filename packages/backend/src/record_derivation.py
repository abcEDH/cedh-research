"""Derive tournament standings from completed TopDeck round tables."""

from __future__ import annotations

from typing import Any


def derive_standing_results(rounds: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Derive player records from completed round tables.

    TopDeck can publish standings with a points total but zero or missing W/L/D
    fields (and, in the same payload, publish zero points for players who have
    completed games). The table results are the authoritative result-level
    source in that case. Players without a usable table result are omitted so
    callers can retain the organizer's standing row for them.
    """
    results: dict[str, dict[str, int]] = {}

    for round_data in rounds or []:
        for table in round_data.get("tables", []) or []:
            status = table.get("status")
            if status is not None and str(status).strip().lower() not in {"completed", "complete"}:
                continue

            players = table.get("players", []) or []
            player_ids = [str(player.get("id")) for player in players if player.get("id") is not None]
            if not player_ids:
                continue

            winner_id = table.get("winner_id")
            if winner_id is None:
                winner_id = table.get("winnerId")
            is_draw = str(winner_id).lower() in {"draw", "_draw_"}
            winner_id = None if is_draw or winner_id is None else str(winner_id)

            # A result without a winner is not a completed result. Do not turn
            # an active/pending table into losses for every participant.
            if winner_id is None and not is_draw:
                continue

            for player_id in player_ids:
                stats = results.setdefault(player_id, {"wins": 0, "losses": 0, "draws": 0, "points": 0})
                if is_draw:
                    stats["draws"] += 1
                    stats["points"] += 1
                elif player_id == winner_id:
                    stats["wins"] += 1
                    stats["points"] += 5
                else:
                    stats["losses"] += 1

    return results
