#!/usr/bin/env python3
"""Export player matchup data to CSV files."""

import csv
import re
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from supabase_client import get_supabase_client

ELO_TIERS = {"ranking", "local", "all"}
ELO_TIER_LABELS = {
    "ranking": "Tier 1: Ranking ELO",
    "local": "Tier 2: Local / Regional ELO",
    "all": "Tier 3: All Games",
}
GAME_ID_BATCH_SIZE = 500
PARTICIPANT_PAGE_SIZE = 1000


def validate_tier(tier: str) -> str:
    if tier not in ELO_TIERS:
        raise ValueError(f"tier must be one of: {', '.join(sorted(ELO_TIERS))}")
    return tier


def is_tier_eligible(tier: str, tournament: dict, entry: dict, game_status: str | None = None) -> bool:
    """Apply the canonical issue #288 eligibility rules to one player entry."""
    validate_tier(tier)
    start_date = tournament.get("start_date")
    if not start_date:
        return False
    if tier == "all":
        return True
    try:
        if datetime.fromisoformat(start_date.replace("Z", "+00:00")).date() > datetime.now().date():
            return False
    except ValueError:
        return False
    if game_status and game_status.lower() not in {"completed", "complete", "done"}:
        return False

    event_name = str(tournament.get("name") or "")
    if re.search(r"casual|exhibition|\bfun\b", event_name, re.IGNORECASE):
        return False
    if (tournament.get("player_count") or 0) < (30 if tier == "ranking" else 10):
        return False
    if tier == "ranking":
        tournament_key = f"{tournament.get('topdeck_tid') or ''} {event_name}"
        if re.search(r"league", tournament_key, re.IGNORECASE):
            return False
        if not str(entry.get("decklist_text") or "").strip() and not str(entry.get("decklist_url") or "").strip():
            return False
    return True


def fetch_game_participants(client, game_ids: list[str], select: str) -> list[dict]:
    """Fetch every participant row without crossing PostgREST's page limit."""
    participants = []
    for start in range(0, len(game_ids), GAME_ID_BATCH_SIZE):
        batch = game_ids[start : start + GAME_ID_BATCH_SIZE]
        offset = 0
        while True:
            response = (
                client.table("game_participants")
                .select(select)
                .in_("game_id", batch)
                .range(offset, offset + PARTICIPANT_PAGE_SIZE - 1)
                .execute()
            )
            page = response.data or []
            participants.extend(page)
            if len(page) < PARTICIPANT_PAGE_SIZE:
                break
            offset += PARTICIPANT_PAGE_SIZE
    return participants


def export_player_matchups(player_name: str, output_file: str = None, tier: str = "ranking") -> str:
    """
    Export a specific player's matchup data to CSV.

    Args:
        player_name: Name of player to export (e.g., "Jason Doan // CriticalEDH")
        output_file: Output filename (defaults to {player_name}_matchups.csv)

    Returns:
        Path to output file
    """
    validate_tier(tier)
    client = get_supabase_client()

    if not output_file:
        safe_name = player_name.replace(" ", "_").replace("//", "").lower()
        output_file = f"{safe_name}_{tier}_matchups.csv"

    print(f"Fetching data for {player_name}...")

    # Get player
    response = client.table("players").select("id, name, topdeck_id").ilike("name", f"%{player_name}%").execute()
    if not response.data:
        print(f"Player '{player_name}' not found")
        return None

    player = response.data[0]
    player_id = player["id"]
    print(f"Found: {player['name']}")

    # Get all tournament entries
    response = client.table("tournament_entries").select(
        "id, tournament_id, decklist_text, decklist_url"
    ).eq("player_id", player_id).execute()
    entries = {entry["id"]: entry for entry in response.data}
    entry_ids = list(entries)
    print(f"Player has {len(entry_ids)} tournament entries")

    # Get all games - batch fetch
    all_games = []
    for i in range(0, len(entry_ids), 100):
        batch = entry_ids[i:i+100]
        response = client.table("game_participants").select(
            "game_id, entry_id, result"
        ).in_("entry_id", batch).execute()
        all_games.extend(response.data)

    print(f"Found {len(all_games)} game results")

    # Get unique game IDs
    game_ids = list({g["game_id"] for g in all_games})
    print(f"Unique games: {len(game_ids)}")

    # Get all game participants - batch
    all_participants = fetch_game_participants(
        client, game_ids, "game_id, entry_id, result"
    )

    # Get tournament info for each game - batch
    games = {}
    for i in range(0, len(game_ids), 500):
        batch = game_ids[i:i+500]
        response = client.table("games").select("id, tournament_id, status").in_("id", batch).execute()
        for g in response.data:
            games[g["id"]] = g

    # Get tournament info
    tournament_ids = list({g["tournament_id"] for g in games.values()})
    tournaments = {}
    for i in range(0, len(tournament_ids), 500):
        batch = tournament_ids[i:i+500]
        response = client.table("tournaments").select(
            "id, name, start_date, topdeck_tid, player_count"
        ).in_("id", batch).execute()
        for t in response.data:
            tournaments[t["id"]] = t

    # Map entries to players
    opponent_entry_ids = {gp["entry_id"] for gp in all_participants} - set(entry_ids)

    entry_to_player = {}
    for i in range(0, len(opponent_entry_ids), 500):
        batch = list(opponent_entry_ids)[i:i+500]
        response = client.table("tournament_entries").select(
            "id, player_id"
        ).in_("id", batch).execute()
        for e in response.data:
            entry_to_player[e["id"]] = e["player_id"]

    # Get opponent player info
    opponent_player_ids = set(entry_to_player.values())
    players = {}
    for i in range(0, len(opponent_player_ids), 500):
        batch = list(opponent_player_ids)[i:i+500]
        response = client.table("players").select(
            "id, name, topdeck_id"
        ).in_("id", batch).execute()
        for p in response.data:
            players[p["id"]] = p

    # Create CSV data
    csv_rows = []
    jason_game_results = {gp["game_id"]: gp["result"] for gp in all_games}
    player_entry_by_game = {
        game["game_id"]: game["entry_id"] for game in all_games
    }
    eligible_game_ids = {
        game_id
        for game_id, game in games.items()
        if is_tier_eligible(
            tier,
            tournaments.get(game["tournament_id"], {}),
            entries.get(player_entry_by_game.get(game_id), {}),
            game.get("status"),
        )
    }

    for game_id in game_ids:
        if game_id not in eligible_game_ids:
            continue
        game = games.get(game_id)
        tournament = tournaments.get(game["tournament_id"]) if game else None

        game_participants = [gp for gp in all_participants if gp["game_id"] == game_id]
        jason_result = jason_game_results.get(game_id, "unknown")

        for gp in game_participants:
            if gp["entry_id"] in entry_ids:
                continue

            opponent_player_id = entry_to_player.get(gp["entry_id"])
            opponent = players.get(opponent_player_id) if opponent_player_id else None

            if opponent:
                csv_rows.append({
                    "date": tournament["start_date"].split("T")[0] if tournament else "unknown",
                    "tournament": tournament["name"] if tournament else "unknown",
                    "player": player["name"],
                    "player_result": jason_result.upper(),
                    "opponent": opponent["name"],
                    "opponent_topdeck_id": opponent["topdeck_id"],
                })

    # Write CSV
    print(f"Writing {len(csv_rows)} game records to {output_file}...")

    with open(output_file, 'w', newline='') as f:
        f.write(f"# ELO Tier: {ELO_TIER_LABELS[tier]}\n")
        f.write(f"# Eligibility: {tier}\n")
        writer = csv.DictWriter(f, fieldnames=[
            "date", "tournament", "player", "player_result", "opponent", "opponent_topdeck_id"
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"✓ Exported to {output_file}")
    return output_file


def export_matchup_summary(player_name: str, output_file: str = None, tier: str = "ranking") -> str:
    """
    Export aggregated matchup stats (wins/losses by opponent).

    Args:
        player_name: Name of player to export
        output_file: Output filename (defaults to {player_name}_summary.csv)

    Returns:
        Path to output file
    """
    validate_tier(tier)
    client = get_supabase_client()

    if not output_file:
        safe_name = player_name.replace(" ", "_").replace("//", "").lower()
        output_file = f"{safe_name}_{tier}_summary.csv"

    print(f"Fetching summary data for {player_name}...")

    # Get player
    response = client.table("players").select("id, name, topdeck_id").ilike("name", f"%{player_name}%").execute()
    if not response.data:
        print(f"Player '{player_name}' not found")
        return None

    player = response.data[0]
    player_id = player["id"]

    # Get all entries
    response = client.table("tournament_entries").select(
        "id, tournament_id, decklist_text, decklist_url"
    ).eq("player_id", player_id).execute()
    entries = {entry["id"]: entry for entry in response.data}
    entry_ids = list(entries)

    # Get all games - batch
    all_games = []
    for i in range(0, len(entry_ids), 100):
        batch = entry_ids[i:i+100]
        response = client.table("game_participants").select(
            "game_id, entry_id, result"
        ).in_("entry_id", batch).execute()
        all_games.extend(response.data)

    game_ids = list({g["game_id"] for g in all_games})

    games = {}
    for i in range(0, len(game_ids), 500):
        batch = game_ids[i:i+500]
        response = client.table("games").select("id, tournament_id, status").in_("id", batch).execute()
        games.update({game["id"]: game for game in response.data})

    tournament_ids = list({game["tournament_id"] for game in games.values()})
    tournaments = {}
    for i in range(0, len(tournament_ids), 500):
        batch = tournament_ids[i:i+500]
        response = client.table("tournaments").select(
            "id, name, start_date, topdeck_tid, player_count"
        ).in_("id", batch).execute()
        tournaments.update({tournament["id"]: tournament for tournament in response.data})

    player_entry_by_game = {
        game["game_id"]: game["entry_id"] for game in all_games
    }
    eligible_game_ids = {
        game_id
        for game_id, game in games.items()
        if is_tier_eligible(
            tier,
            tournaments.get(game["tournament_id"], {}),
            entries.get(player_entry_by_game.get(game_id), {}),
            game.get("status"),
        )
    }

    # Get all participants
    all_participants = fetch_game_participants(client, game_ids, "game_id, entry_id")

    # Map to opponent data
    opponent_entry_ids = {gp["entry_id"] for gp in all_participants} - set(entry_ids)

    entry_to_player = {}
    for i in range(0, len(opponent_entry_ids), 500):
        batch = list(opponent_entry_ids)[i:i+500]
        response = client.table("tournament_entries").select(
            "id, player_id"
        ).in_("id", batch).execute()
        for e in response.data:
            entry_to_player[e["id"]] = e["player_id"]

    opponent_player_ids = set(entry_to_player.values())
    players = {}
    for i in range(0, len(opponent_player_ids), 500):
        batch = list(opponent_player_ids)[i:i+500]
        response = client.table("players").select(
            "id, name, topdeck_id"
        ).in_("id", batch).execute()
        for p in response.data:
            players[p["id"]] = p

    # Build matchup stats
    matchups = {}
    jason_game_results = {gp["game_id"]: gp["result"] for gp in all_games}

    for game_id in game_ids:
        if game_id not in eligible_game_ids:
            continue
        jason_result = jason_game_results.get(game_id, "unknown")

        game_participants = [gp for gp in all_participants if gp["game_id"] == game_id]

        for gp in game_participants:
            if gp["entry_id"] in entry_ids:
                continue

            opponent_player_id = entry_to_player.get(gp["entry_id"])
            opponent = players.get(opponent_player_id)

            if opponent:
                key = (opponent["name"], opponent["topdeck_id"])
                if key not in matchups:
                    matchups[key] = {"wins": 0, "losses": 0, "draws": 0}

                result_lower = jason_result.lower()
                if result_lower == "win":
                    matchups[key]["wins"] += 1
                elif result_lower == "loss":
                    matchups[key]["losses"] += 1
                elif result_lower == "draw":
                    matchups[key]["draws"] += 1

    # Convert to CSV rows
    csv_rows = []
    for (opponent_name, opponent_id), stats in sorted(
        matchups.items(),
        key=lambda x: x[1]["wins"] + x[1]["losses"] + x[1]["draws"],
        reverse=True
    ):
        total = stats["wins"] + stats["losses"] + stats["draws"]
        win_pct = (stats["wins"] / total * 100) if total > 0 else 0

        csv_rows.append({
            "opponent": opponent_name,
            "opponent_topdeck_id": opponent_id,
            "games": total,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "draws": stats["draws"],
            "win_pct": f"{win_pct:.1f}%",
        })

    # Write CSV
    print(f"Writing {len(csv_rows)} opponent summaries to {output_file}...")

    with open(output_file, 'w', newline='') as f:
        f.write(f"# ELO Tier: {ELO_TIER_LABELS[tier]}\n")
        f.write(f"# Eligibility: {tier}\n")
        writer = csv.DictWriter(f, fieldnames=[
            "opponent", "opponent_topdeck_id", "games", "wins", "losses", "draws", "win_pct"
        ])
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"✓ Exported to {output_file}")
    return output_file


if __name__ == "__main__":
    player = "Jason Doan // CriticalEDH"

    print(f"=== Exporting data for {player} ===\n")

    # Export both detailed and summary
    detail_file = export_player_matchups(player, tier="ranking")
    summary_file = export_matchup_summary(player, tier="ranking")

    if detail_file and summary_file:
        print("\n✓ Done! Files ready for sharing:")
        print(f"  - Detailed games: {detail_file}")
        print(f"  - Summary stats: {summary_file}")
