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
  result?: string;
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

const GAME_PARTICIPANT_PAGE_SIZE = 1000;
const GAME_ID_BATCH_SIZE = 200;
const LOOKUP_BATCH_SIZE = 500;

export class AmbiguousPlayerMatchError extends Error {
  constructor(playerName: string) {
    super(`Multiple players matched "${playerName}". Use the exact player name.`);
    this.name = "AmbiguousPlayerMatchError";
  }
}

async function fetchPlayerByName(playerName: string): Promise<Player | null> {
  const { data: exactPlayers, error: exactPlayerError } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .eq("name", playerName)
    .limit(1);

  if (exactPlayerError) throw exactPlayerError;
  if (exactPlayers && exactPlayers.length > 0) {
    return exactPlayers[0] as Player;
  }

  const { data: partialPlayers, error: partialPlayerError } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .ilike("name", `%${playerName}%`)
    .limit(2);

  if (partialPlayerError) throw partialPlayerError;

  const players = (partialPlayers || []) as Player[];
  const normalizedName = playerName.trim().toLocaleLowerCase();
  const caseInsensitiveExact = players.find(
    (player) => player.name.trim().toLocaleLowerCase() === normalizedName
  );

  if (caseInsensitiveExact) {
    return caseInsensitiveExact;
  }
  if (players.length > 1) {
    throw new AmbiguousPlayerMatchError(playerName);
  }

  return players[0] || null;
}

async function fetchPlayerGameParticipants(
  entryIds: string[]
): Promise<GameParticipant[]> {
  const rows: GameParticipant[] = [];

  for (let start = 0; start < entryIds.length; start += GAME_ID_BATCH_SIZE) {
    const entryIdBatch = entryIds.slice(start, start + GAME_ID_BATCH_SIZE);

    for (let offset = 0; ; offset += GAME_PARTICIPANT_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("game_participants")
        .select("game_id, entry_id, result")
        .in("entry_id", entryIdBatch)
        .range(offset, offset + GAME_PARTICIPANT_PAGE_SIZE - 1);

      if (error) throw error;

      const page = (data || []) as GameParticipant[];
      rows.push(...page);
      if (page.length < GAME_PARTICIPANT_PAGE_SIZE) break;
    }
  }

  return rows;
}

async function fetchGameParticipants(gameIds: string[]): Promise<GameParticipant[]> {
  const rows: GameParticipant[] = [];

  for (let start = 0; start < gameIds.length; start += GAME_ID_BATCH_SIZE) {
    const gameIdBatch = gameIds.slice(start, start + GAME_ID_BATCH_SIZE);

    for (let offset = 0; ; offset += GAME_PARTICIPANT_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("game_participants")
        .select("game_id, entry_id, result")
        .in("game_id", gameIdBatch)
        .range(offset, offset + GAME_PARTICIPANT_PAGE_SIZE - 1);

      if (error) throw error;

      const page = (data || []) as GameParticipant[];
      rows.push(...page);
      if (page.length < GAME_PARTICIPANT_PAGE_SIZE) break;
    }
  }

  return rows;
}

async function fetchGames(gameIds: string[]): Promise<Game[]> {
  const rows: Game[] = [];

  for (let start = 0; start < gameIds.length; start += GAME_ID_BATCH_SIZE) {
    const gameIdBatch = gameIds.slice(start, start + GAME_ID_BATCH_SIZE);
    const { data, error } = await supabase
      .from("games")
      .select("id, tournament_id, status")
      .in("id", gameIdBatch);

    if (error) throw error;
    rows.push(...((data || []) as Game[]));
  }

  return rows;
}

async function fetchEntryToPlayerMap(entryIds: string[]): Promise<Map<string, string>> {
  const entryToPlayerMap = new Map<string, string>();

  for (let start = 0; start < entryIds.length; start += LOOKUP_BATCH_SIZE) {
    const batch = entryIds.slice(start, start + LOOKUP_BATCH_SIZE);
    const { data, error } = await supabase
      .from("tournament_entries")
      .select("id, player_id")
      .in("id", batch);

    if (error) throw error;
    (data || []).forEach((entry: { id: string; player_id: string }) => {
      entryToPlayerMap.set(entry.id, entry.player_id);
    });
  }

  return entryToPlayerMap;
}

async function fetchPlayerMap(playerIds: string[]): Promise<Map<string, Player>> {
  const playerMap = new Map<string, Player>();

  for (let start = 0; start < playerIds.length; start += LOOKUP_BATCH_SIZE) {
    const batch = playerIds.slice(start, start + LOOKUP_BATCH_SIZE);
    const { data, error } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .in("id", batch);

    if (error) throw error;
    (data || []).forEach((player: Player) => {
      playerMap.set(player.id, player);
    });
  }

  return playerMap;
}

export async function exportPlayerMatchups(
  playerName: string,
  tier: EloTier = "ranking"
): Promise<string | null> {
  const player = await fetchPlayerByName(playerName);
  if (!player) {
    return null;
  }

  const playerId = player.id;

  const { data: entries, error: entriesError } = await supabase
    .from("tournament_entries")
    .select("id")
    .eq("player_id", playerId);

  if (entriesError) throw entriesError;

  const entryIds = (entries || []).map((e) => e.id);

  if (entryIds.length === 0) {
    return "[]";
  }

  const playerGames = await fetchPlayerGameParticipants(entryIds);

  const allGames = playerGames;
  const gameIds = [...new Set(allGames.map((g) => g.game_id))];
  const playerGameResults = Object.fromEntries(
    allGames.map((g) => [g.game_id, g.result])
  );

  if (gameIds.length === 0) {
    return "[]";
  }

  const gameParticipants = await fetchGameParticipants(gameIds);

  const gameData = await fetchGames(gameIds);

  const games = Object.fromEntries(
    gameData.map((g: Game) => [g.id, g])
  );

  const tournamentIds = [
    ...new Set(Object.values(games).map((g: Game) => g.tournament_id)),
  ];
  const { data: tournamentData, error: tournamentError } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid, player_count")
    .in("id", tournamentIds);

  if (tournamentError) throw tournamentError;

  const tournaments = Object.fromEntries(
    (tournamentData || []).map((t: Tournament) => [t.id, t])
  );
  const eligibleGameIds = new Set(
    gameIds.filter((gameId) => {
      const game = games[gameId];
      return isEloTierEligible(
        tier,
        game ? tournaments[game.tournament_id] : null,
        game?.status
      );
    })
  );

  const opponentEntryIds = new Set(
    gameParticipants.map((gp) => gp.entry_id).filter((id) => !entryIds.includes(id))
  );

  const entryToPlayerMap = await fetchEntryToPlayerMap(Array.from(opponentEntryIds));

  const opponentPlayerIds = new Set(entryToPlayerMap.values());
  const playerMap = await fetchPlayerMap(Array.from(opponentPlayerIds));

  const rows: MatchupRow[] = [];

  for (const gameId of gameIds) {
    if (!eligibleGameIds.has(gameId)) continue;
    const game = games[gameId];
    const tournament = game ? tournaments[game.tournament_id] : null;
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
        rows.push({
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

  return JSON.stringify(rows);
}

export async function exportMatchupSummary(
  playerName: string,
  tier: EloTier = "ranking"
): Promise<string | null> {
  const player = await fetchPlayerByName(playerName);
  if (!player) {
    return null;
  }

  const playerId = player.id;

  const { data: entries, error: entriesError } = await supabase
    .from("tournament_entries")
    .select("id")
    .eq("player_id", playerId);

  if (entriesError) throw entriesError;

  const entryIds = (entries || []).map((e) => e.id);

  if (entryIds.length === 0) {
    return "[]";
  }

  const playerGames = await fetchPlayerGameParticipants(entryIds);

  const allGames = playerGames;
  const gameIds = [...new Set(allGames.map((g) => g.game_id))];
  const playerGameResults = Object.fromEntries(
    allGames.map((g) => [g.game_id, g.result])
  );

  if (gameIds.length === 0) {
    return "[]";
  }

  const gameParticipants = await fetchGameParticipants(gameIds);

  const gameData = await fetchGames(gameIds);
  const games = Object.fromEntries(
    gameData.map((g: Game) => [g.id, g])
  );
  const tournamentIds = [
    ...new Set(Object.values(games).map((g: Game) => g.tournament_id)),
  ];
  const { data: tournamentData, error: tournamentError } = await supabase
    .from("tournaments")
    .select("id, name, start_date, topdeck_tid, player_count")
    .in("id", tournamentIds);

  if (tournamentError) throw tournamentError;
  const tournaments = Object.fromEntries(
    (tournamentData || []).map((t: Tournament) => [t.id, t])
  );
  const eligibleGameIds = new Set(
    gameIds.filter((gameId) => {
      const game = games[gameId];
      return isEloTierEligible(
        tier,
        game ? tournaments[game.tournament_id] : null,
        game?.status
      );
    })
  );

  const opponentEntryIds = new Set(
    gameParticipants
      .map((gp) => gp.entry_id)
      .filter((id) => !entryIds.includes(id))
  );

  const entryToPlayerMap = await fetchEntryToPlayerMap(Array.from(opponentEntryIds));

  const opponentPlayerIds = new Set(entryToPlayerMap.values());
  const playerMap = await fetchPlayerMap(Array.from(opponentPlayerIds));

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

  const rows: MatchupSummaryRow[] = Array.from(matchups.entries())
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

  return JSON.stringify(rows);
}
