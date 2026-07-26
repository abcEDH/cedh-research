import { supabase } from "@/lib/supabase";
import { ELO_TIER_INFO, isEloTierEligible, type EloTier } from "@/lib/elo-tiers";

interface MatchupRow {
  date: string;
  tournament: string;
  player: string;
  player_result: string;
  opponent: string;
  opponent_topdeck_id: string;
  elo_tier: EloTier;
  tier_label: string;
  tournament_player_count: number | null;
}

interface MatchupSummaryRow {
  opponent: string;
  opponent_topdeck_id: string;
  games: number;
  wins: number;
  losses: number;
  draws: number;
  win_pct: string;
  elo_tier: EloTier;
  tier_label: string;
}

interface GameParticipant {
  game_id: string;
  entry_id: string;
  result: string;
}

interface TournamentEntry {
  id: string;
  player_id: string;
  tournament_id: string;
  decklist_text: string | null;
  decklist_url: string | null;
}

interface Game {
  id: string;
  tournament_id: string;
  status?: string | null;
}

interface Tournament {
  id: string;
  name: string;
  start_date: string;
  topdeck_tid: string | null;
  player_count: number | null;
}

interface Player {
  id: string;
  name: string;
  topdeck_id: string;
}

function convertToCSV(rows: unknown[]): string {
  if (rows.length === 0) return "";

  const firstRow = rows[0] as Record<string, unknown>;
  const headers = Object.keys(firstRow);
  const csvContent = [
    headers.join(","),
    ...rows.map((row) => {
      const record = row as Record<string, unknown>;
      return headers
        .map((header) => {
          const value = record[header];
          // Escape quotes and wrap in quotes if needed
          const stringValue = String(value || "");
          if (stringValue.includes(",") || stringValue.includes('"')) {
            return `"${stringValue.replace(/"/g, '""')}"`;
          }
          return stringValue;
        })
        .join(",");
    }),
  ].join("\n");

  return csvContent;
}

export async function exportPlayerMatchups(
  playerName: string,
  format: "csv" | "json" = "csv",
  tier: EloTier = "ranking"
): Promise<string | null> {
  // Get player
  const { data: players } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .ilike("name", `%${playerName}%`)
    .limit(1);

  if (!players || players.length === 0) {
    return null;
  }

  const player = players[0] as Player;
  const playerId = player.id;

  // Get all tournament entries for this player
  const { data: entries } = await supabase
    .from("tournament_entries")
    .select("id, player_id, tournament_id, decklist_text, decklist_url")
    .eq("player_id", playerId);

  const entryIds = (entries || []).map((e) => e.id);

  if (entryIds.length === 0) {
    return format === "csv" ? convertToCSV([]) : "[]";
  }

  // Get all games this player participated in
  const { data: playerGames } = await supabase
    .from("game_participants")
    .select("game_id, entry_id, result")
    .in("entry_id", entryIds);

  const allGames = (playerGames || []) as GameParticipant[];
  const gameIds = [...new Set(allGames.map((g) => g.game_id))];
  const playerGameResults = Object.fromEntries(
    allGames.map((g) => [g.game_id, g.result])
  );

  if (gameIds.length === 0) {
    return format === "csv" ? convertToCSV([]) : "[]";
  }

  // Get all participants in these games
  const { data: allParticipants } = await supabase
    .from("game_participants")
    .select("game_id, entry_id, result")
    .in("game_id", gameIds);

  const gameParticipants = (allParticipants || []) as GameParticipant[];

  // Get game info and completion status.
  const { data: gameData } = await supabase
    .from("games")
    .select("id, tournament_id, status")
    .in("id", gameIds);

  const games = Object.fromEntries(
    (gameData || []).map((g: Game) => [g.id, g])
  );

  // Get tournament info
  const tournamentIds = [
    ...new Set(Object.values(games).map((g: Game) => g.tournament_id)),
  ];
  const { data: tournamentData } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid, player_count")
    .in("id", tournamentIds);

  const tournaments = Object.fromEntries(
    (tournamentData || []).map((t: Tournament) => [t.id, t])
  );
  const entriesById = Object.fromEntries(
    ((entries || []) as TournamentEntry[]).map((entry) => [entry.id, entry])
  );
  const playerEntryByGame = Object.fromEntries(
    allGames.map((game) => [game.game_id, game.entry_id])
  );
  const eligibleGameIds = new Set(
    gameIds.filter((gameId) => {
      const game = games[gameId];
      return isEloTierEligible(
        tier,
        game ? tournaments[game.tournament_id] : null,
        entriesById[playerEntryByGame[gameId]],
        game?.status
      );
    })
  );

  // Get opponent entry IDs
  const opponentEntryIds = new Set(
    gameParticipants.map((gp) => gp.entry_id).filter((id) => !entryIds.includes(id))
  );

  // Map entries to player IDs
  const entryToPlayerMap = new Map<string, string>();
  if (opponentEntryIds.size > 0) {
    const { data: entryData } = await supabase
      .from("tournament_entries")
      .select("id, player_id")
      .in("id", Array.from(opponentEntryIds));

    (entryData || []).forEach((e: { id: string; player_id: string }) => {
      entryToPlayerMap.set(e.id, e.player_id);
    });
  }

  // Get opponent player info
  const opponentPlayerIds = new Set(entryToPlayerMap.values());
  const playerMap = new Map<string, Player>();
  if (opponentPlayerIds.size > 0) {
    const { data: opponentData } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .in("id", Array.from(opponentPlayerIds));

    (opponentData || []).forEach((p: Player) => {
      playerMap.set(p.id, p);
    });
  }

  // Build matchup rows
  const csvRows: MatchupRow[] = [];

  for (const gameId of gameIds) {
    if (!eligibleGameIds.has(gameId)) continue;
    const game = games[gameId];
    const tournament = game ? tournaments[game.tournament_id] : null;
    const playerResult = playerGameResults[gameId] || "unknown";

    const gameParticipantsForGame = gameParticipants.filter(
      (gp) => gp.game_id === gameId
    );

    for (const gp of gameParticipantsForGame) {
      // Skip the player's own entry
      if (entryIds.includes(gp.entry_id)) {
        continue;
      }

      const opponentPlayerId = entryToPlayerMap.get(gp.entry_id);
      const opponent = opponentPlayerId ? playerMap.get(opponentPlayerId) : null;

      if (opponent) {
        csvRows.push({
          date: tournament ? tournament.start_date.split("T")[0] : "unknown",
          tournament: tournament?.name || "unknown",
          player: player.name,
          player_result: playerResult.toUpperCase(),
          opponent: opponent.name,
          opponent_topdeck_id: opponent.topdeck_id,
          elo_tier: tier,
          tier_label: ELO_TIER_INFO[tier].label,
          tournament_player_count: tournament?.player_count ?? null,
        });
      }
    }
  }

  if (format === "json") {
    return JSON.stringify(csvRows);
  }

  return convertToCSV(csvRows);
}

export async function exportMatchupSummary(
  playerName: string,
  format: "csv" | "json" = "csv",
  tier: EloTier = "ranking"
): Promise<string | null> {
  // Get player
  const { data: players } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .ilike("name", `%${playerName}%`)
    .limit(1);

  if (!players || players.length === 0) {
    return null;
  }

  const player = players[0] as Player;
  const playerId = player.id;

  // Get all entries
  const { data: entries } = await supabase
    .from("tournament_entries")
    .select("id, player_id, tournament_id, decklist_text, decklist_url")
    .eq("player_id", playerId);

  const entryIds = (entries || []).map((e) => e.id);

  if (entryIds.length === 0) {
    return format === "csv" ? convertToCSV([]) : "[]";
  }

  // Get all games
  const { data: playerGames } = await supabase
    .from("game_participants")
    .select("game_id, entry_id, result")
    .in("entry_id", entryIds);

  const allGames = (playerGames || []) as GameParticipant[];
  const gameIds = [...new Set(allGames.map((g) => g.game_id))];
  const playerGameResults = Object.fromEntries(
    allGames.map((g) => [g.game_id, g.result])
  );

  if (gameIds.length === 0) {
    return format === "csv" ? convertToCSV([]) : "[]";
  }

  // Get all participants
  const { data: allParticipants } = await supabase
    .from("game_participants")
    .select("game_id, entry_id")
    .in("game_id", gameIds);

  const gameParticipants = (allParticipants || []) as GameParticipant[];

  const { data: gameData } = await supabase
    .from("games")
    .select("id, tournament_id, status")
    .in("id", gameIds);
  const games = Object.fromEntries(
    (gameData || []).map((g: Game) => [g.id, g])
  );
  const tournamentIds = [
    ...new Set(Object.values(games).map((g: Game) => g.tournament_id)),
  ];
  const { data: tournamentData } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid, player_count")
    .in("id", tournamentIds);
  const tournaments = Object.fromEntries(
    (tournamentData || []).map((t: Tournament) => [t.id, t])
  );
  const entriesById = Object.fromEntries(
    ((entries || []) as TournamentEntry[]).map((entry) => [entry.id, entry])
  );
  const playerEntryByGame = Object.fromEntries(
    allGames.map((game) => [game.game_id, game.entry_id])
  );
  const eligibleGameIds = new Set(
    gameIds.filter((gameId) => {
      const game = games[gameId];
      return isEloTierEligible(
        tier,
        game ? tournaments[game.tournament_id] : null,
        entriesById[playerEntryByGame[gameId]],
        game?.status
      );
    })
  );

  // Get opponent entries
  const opponentEntryIds = new Set(
    gameParticipants
      .map((gp) => gp.entry_id)
      .filter((id) => !entryIds.includes(id))
  );

  // Map entries to player IDs
  const entryToPlayerMap = new Map<string, string>();
  if (opponentEntryIds.size > 0) {
    const { data: entryData } = await supabase
      .from("tournament_entries")
      .select("id, player_id")
      .in("id", Array.from(opponentEntryIds));

    (entryData || []).forEach((e: { id: string; player_id: string }) => {
      entryToPlayerMap.set(e.id, e.player_id);
    });
  }

  // Get opponent player info
  const opponentPlayerIds = new Set(entryToPlayerMap.values());
  const playerMap = new Map<string, Player>();
  if (opponentPlayerIds.size > 0) {
    const { data: opponentData } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .in("id", Array.from(opponentPlayerIds));

    (opponentData || []).forEach((p: Player) => {
      playerMap.set(p.id, p);
    });
  }

  // Build matchup stats
  const matchups = new Map<
    string,
    { wins: number; losses: number; draws: number }
  >();

  for (const gameId of gameIds) {
    if (!eligibleGameIds.has(gameId)) continue;
    const playerResult = playerGameResults[gameId] || "unknown";
    const gameParticipantsForGame = gameParticipants.filter(
      (gp) => gp.game_id === gameId
    );

    for (const gp of gameParticipantsForGame) {
      if (entryIds.includes(gp.entry_id)) {
        continue;
      }

      const opponentPlayerId = entryToPlayerMap.get(gp.entry_id);
      const opponent = opponentPlayerId ? playerMap.get(opponentPlayerId) : null;

      if (opponent) {
        const key = `${opponent.name}|${opponent.topdeck_id}`;
        if (!matchups.has(key)) {
          matchups.set(key, { wins: 0, losses: 0, draws: 0 });
        }

        const stats = matchups.get(key)!;
        const resultLower = playerResult.toLowerCase();
        if (resultLower === "win") {
          stats.wins++;
        } else if (resultLower === "loss") {
          stats.losses++;
        } else if (resultLower === "draw") {
          stats.draws++;
        }
      }
    }
  }

  // Convert to CSV rows, sorted by total games
  const csvRows: MatchupSummaryRow[] = Array.from(matchups.entries())
    .sort(
      (a, b) =>
        b[1].wins +
        b[1].losses +
        b[1].draws -
        (a[1].wins + a[1].losses + a[1].draws)
    )
    .map(([key, stats]) => {
      const [opponentName, opponentId] = key.split("|");
      const total = stats.wins + stats.losses + stats.draws;
      const winPct = total > 0 ? ((stats.wins / total) * 100).toFixed(1) : "0.0";

      return {
        opponent: opponentName,
        opponent_topdeck_id: opponentId,
        games: total,
        wins: stats.wins,
        losses: stats.losses,
        draws: stats.draws,
        win_pct: `${winPct}%`,
        elo_tier: tier,
        tier_label: ELO_TIER_INFO[tier].label,
      };
    });

  if (format === "json") {
    return JSON.stringify(csvRows);
  }

  return convertToCSV(csvRows);
}
