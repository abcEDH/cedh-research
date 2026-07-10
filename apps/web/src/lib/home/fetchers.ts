import { supabase } from "@/lib/supabase";

export interface LeaderboardPlayer {
  player_id: string;
  topdeck_id: string;
  player_name: string;
  rank: number;
  topdeck_elo: number | null;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  active_commander: string | null;
  active_commander_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
}

export function isKnownCommanderName(value: string | null | undefined): value is string {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

export async function getLeaderboardPreview(): Promise<LeaderboardPlayer[]> {
  try {
    const { data, error } = await supabase
      .from("global_elo_active_leaderboard")
      .select(
        "player_id, player_name, topdeck_id, rank, topdeck_elo, topdeck_elo_rank, games_played, wins, draws, losses, last_game_date"
      )
      .eq("region_type", "global")
      .eq("region_key", "ALL")
      .order("topdeck_elo_rank", { ascending: true, nullsFirst: false })
      .order("rank", { ascending: true })
      .limit(10);

    if (error) {
      console.error("Error fetching home leaderboard preview:", error);
      return [];
    }

    const leaderboardRows = ((data ?? []) as Array<{
      player_id: string;
      player_name: string;
      topdeck_id: string | null;
      rank: number | null;
      topdeck_elo: number | null;
      topdeck_elo_rank: number | null;
      games_played: number;
      wins: number;
      draws: number;
      losses: number;
      last_game_date: string | null;
    }>).filter((row) => row.topdeck_id);

    const topdeckIds = leaderboardRows
      .map((row) => row.topdeck_id)
      .filter((value): value is string => Boolean(value));
    const [profileByTopdeckId, latestTournamentByPlayerId] = await Promise.all([
      fetchHomeLeaderboardProfiles(topdeckIds),
      fetchHomeLeaderboardLatestTournaments(leaderboardRows.map((row) => row.player_id)),
    ]);

    return leaderboardRows.map((row, index) => {
      const topdeckId = row.topdeck_id ?? "";
      const profile = profileByTopdeckId.get(topdeckId);
      const latestTournament = latestTournamentByPlayerId.get(row.player_id);
      return {
        player_id: row.player_id,
        topdeck_id: topdeckId,
        player_name: row.player_name,
        rank: row.topdeck_elo_rank ?? row.rank ?? index + 1,
        topdeck_elo: row.topdeck_elo,
        games_played: row.games_played,
        wins: row.wins,
        draws: row.draws,
        losses: row.losses,
        last_game_date: row.last_game_date,
        active_commander: isKnownCommanderName(profile?.active_commander)
          ? profile?.active_commander ?? null
          : null,
        active_commander_decklist_url: profile?.latest_decklist_url ?? null,
        latest_tournament_name: latestTournament?.name ?? null,
        latest_tournament_date: latestTournament?.date ?? null,
        latest_tournament_topdeck_tid: latestTournament?.topdeck_tid ?? null,
      };
    });
  } catch (error) {
    console.error("Error fetching home leaderboard preview:", error);
    return [];
  }
}

async function fetchHomeLeaderboardProfiles(topdeckIds: string[]) {
  if (topdeckIds.length === 0) {
    return new Map<string, {
      active_commander: string | null;
      latest_decklist_url: string | null;
    }>();
  }

  const { data, error } = await supabase
    .from("player_commander_profiles")
    .select("topdeck_id, active_commander, latest_decklist_url")
    .in("topdeck_id", topdeckIds);

  if (error) {
    console.error("Error fetching home leaderboard profiles:", error);
    return new Map();
  }

  return new Map(
    ((data ?? []) as Array<{
      topdeck_id: string | null;
      active_commander: string | null;
      latest_decklist_url: string | null;
    }>)
      .filter((row) => row.topdeck_id)
      .map((row) => [row.topdeck_id as string, row])
  );
}

async function fetchHomeLeaderboardLatestTournaments(playerIds: string[]) {
  const uniquePlayerIds = Array.from(new Set(playerIds.filter(Boolean)));
  const latestByPlayerId = new Map<
    string,
    {
      name: string | null;
      date: string | null;
      topdeck_tid: string | null;
      tournament_id: string | null;
    }
  >();
  if (uniquePlayerIds.length === 0) return latestByPlayerId;

  for (const table of ["global_elo_game_event_log", "regional_elo_game_event_log"]) {
    const { data, error } = await supabase
      .from(table)
      .select("player_id, game_date, tournament_name, tournament_id")
      .in("player_id", uniquePlayerIds)
      .order("game_date", { ascending: false })
      .limit(250);

    if (error) continue;

    for (const row of (data ?? []) as Array<{
      player_id: string;
      game_date: string | null;
      tournament_name: string | null;
      tournament_id: string | null;
    }>) {
      if (latestByPlayerId.has(row.player_id)) continue;
      latestByPlayerId.set(row.player_id, {
        name: row.tournament_name ?? null,
        date: row.game_date ?? null,
        topdeck_tid: null,
        tournament_id: row.tournament_id ?? null,
      });
    }

    if (latestByPlayerId.size > 0) break;
  }

  const tournamentIds = Array.from(
    new Set(
      Array.from(latestByPlayerId.values())
        .map((row) => row.tournament_id)
        .filter((value): value is string => Boolean(value))
    )
  );
  if (tournamentIds.length === 0) return latestByPlayerId;

  const { data, error } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid")
    .in("id", tournamentIds);

  if (error) return latestByPlayerId;

  const tournamentsById = new Map(
    ((data ?? []) as Array<{
      id: string;
      name: string | null;
      start_date: string | null;
      topdeck_tid: string | null;
    }>).map((row) => [row.id, row])
  );

  for (const latest of latestByPlayerId.values()) {
    if (!latest.tournament_id) continue;
    const tournament = tournamentsById.get(latest.tournament_id);
    if (!tournament) continue;
    latest.name = tournament.name ?? latest.name;
    latest.date = tournament.start_date ?? latest.date;
    latest.topdeck_tid = tournament.topdeck_tid ?? null;
  }

  return latestByPlayerId;
}

export async function fetchRecentTournaments() {
  const { data: rows, error } = await supabase
    .from("tournaments")
    .select("id, topdeck_tid, name, start_date, player_count")
    .not("topdeck_tid", "is", null)
    .gte("player_count", 16)
    .order("start_date", { ascending: false })
    .limit(10);

  if (error) throw new Error(`Recent tournaments query failed: ${error.message}`);
  if (!rows?.length) return [];

  const ids = rows.map((r) => r.id);
  const { data: winners, error: winnersError } = await supabase
    .from("tournament_entries")
    .select("tournament_id, players(name, topdeck_handle)")
    .eq("final_standing", 1)
    .in("tournament_id", ids);

  if (winnersError) throw new Error(`Recent tournaments winners query failed: ${winnersError.message}`);

  const winnerMap = new Map((winners ?? []).map((w) => [w.tournament_id, w]));

  return rows.slice(0, 5).map((t) => {
    const winner = winnerMap.get(t.id);
    const player = Array.isArray(winner?.players) ? winner?.players[0] : winner?.players;
    return {
      slug: t.topdeck_tid as string,
      name: (t.name ?? "").trim(),
      date: (t.start_date ?? "").slice(0, 10),
      players: t.player_count ?? 0,
      winner: player?.name ?? (player as { topdeck_handle?: string } | null)?.topdeck_handle ?? "—",
    };
  });
}
