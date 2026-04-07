import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildProfiles, selectCommanderForecastRows, type CommanderUsageRow } from "@/lib/meta-prep";
import { supabase } from "@/lib/supabase";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { inferCountryForRegion } from "@/lib/region-countries";
import { OpponentRecordsTable } from "./opponent-records-table";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";

export const dynamic = "force-dynamic";
const SUPABASE_PAGE_SIZE = 1000;
const SUPABASE_IN_CHUNK_SIZE = 100;

type PlayerRow = {
  id: string;
  name: string;
  topdeck_id: string;
};

type EntryRow = {
  id: string;
  tournament_id: string;
  player_id: string;
  commander_id: string | null;
};

type CommanderRow = {
  id: string;
  name: string;
};

type ParticipantRow = {
  game_id: string;
  entry_id: string;
  seat_position: number;
  result: string;
};

type GameRow = {
  id: string;
  tournament_id: string;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  is_draw: boolean;
  winner_id: string | null;
};

type TournamentRow = {
  id: string;
  name: string;
  start_date: string;
  state: string | null;
};

type LeaderboardRankRow = {
  country_key?: string | null;
  primary_country_key?: string | null;
  primary_region_key?: string | null;
  region_key?: string;
  rank: number;
  rating: number;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

type StateAssignmentRow = {
  country_key: string;
  region_key: string;
  rank: number | null;
  rating: number | null;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

type GlobalSnapshotRow = {
  rank: number;
  points: number;
};

type PlayerCommanderUsageQueryRow = {
  wins: number | null;
  draws: number | null;
  losses: number | null;
  commanders:
    | {
        name: string | null;
      }
    | Array<{
        name: string | null;
      }>
    | null;
  tournaments:
    | {
        start_date: string | null;
        player_count: number | null;
        topdeck_tid: string | null;
      }
    | Array<{
        start_date: string | null;
        player_count: number | null;
        topdeck_tid: string | null;
      }>
    | null;
};

type PlayerCommanderProfileRow = {
  active_commander: string | null;
};

type PlayerEventLogRow = {
  game_id: string;
  game_date: string | null;
  tournament_name: string | null;
  state: string | null;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
};

type PlayerEventOpponentRow = {
  game_id: string;
  player_id: string;
  player_name: string | null;
  topdeck_id: string | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
};

function chunkArray<T>(values: T[], chunkSize: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}

function toRoundLabel(game: GameRow) {
  if (game.round_name) return game.round_name;
  if (game.round_number !== null) return `Round ${game.round_number}`;
  return "Bracket";
}

function toEventRoundLabel(row: PlayerEventLogRow) {
  if (row.round_name) return row.round_name;
  if (row.round_number !== null) return `Round ${row.round_number}`;
  return "Bracket";
}

function isKnownCommanderName(value: string | null | undefined) {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

function firstRelation<T>(value: T | T[] | null) {
  return Array.isArray(value) ? value[0] ?? null : value;
}

function chunkValues<T>(values: T[], size = SUPABASE_IN_CHUNK_SIZE) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += size) {
    chunks.push(values.slice(index, index + size));
  }
  return chunks;
}

function readRegionParam(
  params:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined
) {
  if (!params) return "";
  if (typeof (params as URLSearchParams).get === "function") {
    return (params as URLSearchParams).get("region") ?? "";
  }
  const value = (params as Record<string, string | string[] | undefined>).region;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

async function fetchPlayer(topdeckId: string): Promise<PlayerRow | null> {
  const { data } = await supabase
    .from("players")
    .select("id, name, topdeck_id")
    .eq("topdeck_id", topdeckId)
    .maybeSingle();

  return (data as PlayerRow | null) ?? null;
}

async function fetchEntries(playerId: string): Promise<EntryRow[]> {
  const { data } = await supabase
    .from("tournament_entries")
    .select("id, tournament_id, player_id, commander_id")
    .eq("player_id", playerId);

  return (data as EntryRow[]) ?? [];
}

async function fetchGlobalEloRank(playerId: string): Promise<LeaderboardRankRow | null> {
  const { data } = await supabase
    .from("regional_elo_leaderboard")
    .select("primary_country_key, primary_region_key, rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "global")
    .eq("region_key", "ALL")
    .eq("player_id", playerId)
    .maybeSingle();

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchRegionalRank(playerId: string, regionKey: string): Promise<LeaderboardRankRow | null> {
  if (!regionKey) return null;

  const { data, error } = await supabase
    .from("regional_elo_leaderboard")
    .select("country_key, region_key, rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "state")
    .eq("region_key", regionKey)
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) {
    const { data: fallbackData } = await supabase
      .from("regional_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses")
      .eq("region_type", "state")
      .eq("region_key", regionKey)
      .eq("player_id", playerId)
      .maybeSingle();

    return (fallbackData as LeaderboardRankRow | null) ?? null;
  }

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchRegionalRanks(playerId: string): Promise<LeaderboardRankRow[]> {
  const { data, error } = await supabase
    .from("regional_elo_leaderboard")
    .select("country_key, region_key, rank, rating, games_played, wins, draws, losses")
    .eq("region_type", "state")
    .eq("player_id", playerId)
    .order("rank", { ascending: true });

  if (error) {
    const { data: fallbackData } = await supabase
      .from("regional_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses")
      .eq("region_type", "state")
      .eq("player_id", playerId)
      .order("rank", { ascending: true });

    return ((fallbackData as LeaderboardRankRow[]) ?? []).sort((a, b) => {
      if (a.rank !== b.rank) return a.rank - b.rank;
      return (a.region_key ?? "").localeCompare(b.region_key ?? "");
    });
  }

  return ((data as LeaderboardRankRow[]) ?? []).sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;
    return (a.region_key ?? "").localeCompare(b.region_key ?? "");
  });
}

async function fetchGlobalSnapshot(topdeckId: string): Promise<GlobalSnapshotRow | null> {
  try {
    const leaderboard = await fetchChampionshipLeaderboard();
    const entry = leaderboard.find((row) => row.uid === topdeckId);
    if (!entry) return null;
    return {
      rank: entry.rank,
      points: entry.points,
    };
  } catch {
    return null;
  }
}

function buildTopdeckDecklistUrl(tournamentSlug: string | null | undefined, topdeckId: string) {
  return tournamentSlug ? `https://topdeck.gg/deck/${tournamentSlug}/${topdeckId}` : null;
}

async function fetchPlayerCommanderUsageRows(
  playerId: string,
  topdeckId: string,
  playerName: string
): Promise<CommanderUsageRow[]> {
  const { data, error } = await supabase
    .from("tournament_entries")
    .select("wins, draws, losses, commanders(name), tournaments(start_date, player_count, topdeck_tid)")
    .eq("player_id", playerId);

  if (error) {
    throw new Error(`Error fetching player commander usage: ${error.message}`);
  }

  return ((data ?? []) as PlayerCommanderUsageQueryRow[])
    .map((row) => {
      const commander = firstRelation(row.commanders);
      const tournament = firstRelation(row.tournaments);
      const commanderName = isKnownCommanderName(commander?.name) ? commander?.name ?? null : null;

      return {
        topdeck_id: topdeckId,
        player_name: playerName,
        commander_name: commanderName,
        wins: row.wins,
        draws: row.draws,
        losses: row.losses,
        start_date: tournament?.start_date ?? null,
        player_count: tournament?.player_count ?? null,
        decklist_url: null,
        topdeck_decklist_url: buildTopdeckDecklistUrl(tournament?.topdeck_tid, topdeckId),
      };
    })
    .filter((row) => row.commander_name && row.start_date);
}

async function fetchActiveCommander(playerId: string, topdeckId: string, playerName: string): Promise<string | null> {
  const { data: profileRow, error: profileError } = await supabase
    .from("player_commander_profiles")
    .select("active_commander")
    .eq("topdeck_id", topdeckId)
    .maybeSingle();

  if (!profileError) {
    const profile = profileRow as PlayerCommanderProfileRow | null;
    if (isKnownCommanderName(profile?.active_commander)) {
      return profile?.active_commander ?? null;
    }
  }

  const referenceDate = new Date();
  const usageRows = await fetchPlayerCommanderUsageRows(playerId, topdeckId, playerName);
  const forecastRows = selectCommanderForecastRows([topdeckId], usageRows, referenceDate);
  const profiles = buildProfiles(
    [topdeckId],
    forecastRows,
    1,
    referenceDate.toISOString()
  );

  return profiles.players[0]?.commanders[0]?.commander ?? null;
}

async function fetchGamesAndParticipants(entryIds: string[]) {
  const participants: ParticipantRow[] = [];
  for (const entryIdChunk of chunkValues(entryIds)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("game_participants")
        .select("game_id, entry_id, seat_position, result")
        .in("entry_id", entryIdChunk)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (error) throw new Error(`Error fetching player game participants: ${error.message}`);
      participants.push(...((data as ParticipantRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  const gameIds = Array.from(new Set(participants.map((row) => row.game_id)));
  if (gameIds.length === 0) {
    return {
      participants: [],
      games: [] as GameRow[],
      allParticipants: [] as ParticipantRow[],
    };
  }

  const games: GameRow[] = [];
  const allParticipants: ParticipantRow[] = [];

  for (const gameIdChunk of chunkValues(gameIds)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("games")
        .select("id, tournament_id, round_number, round_name, table_number, is_draw, winner_id")
        .in("id", gameIdChunk)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (error) throw new Error(`Error fetching player games: ${error.message}`);
      games.push(...((data as GameRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  for (const gameIdChunk of chunkValues(gameIds)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("game_participants")
        .select("game_id, entry_id, seat_position, result")
        .in("game_id", gameIdChunk)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (error) throw new Error(`Error fetching pod participants: ${error.message}`);
      allParticipants.push(...((data as ParticipantRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  return {
    participants,
    games,
    allParticipants,
  };
}

async function fetchTournaments(tournamentIds: string[]): Promise<Map<string, TournamentRow>> {
  if (tournamentIds.length === 0) return new Map();

  const rows: TournamentRow[] = [];
  for (const tournamentIdChunk of chunkValues(tournamentIds)) {
    const { data, error } = await supabase
      .from("tournaments")
      .select("id, name, start_date, state")
      .in("id", tournamentIdChunk);

    if (error) throw new Error(`Error fetching tournaments: ${error.message}`);
    rows.push(...((data as TournamentRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchEntriesById(entryIds: string[]): Promise<Map<string, EntryRow>> {
  if (entryIds.length === 0) return new Map();

  const rows: EntryRow[] = [];
  for (const entryIdChunk of chunkValues(entryIds)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("tournament_entries")
        .select("id, tournament_id, player_id, commander_id")
        .in("id", entryIdChunk)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (error) throw new Error(`Error fetching related tournament entries: ${error.message}`);
      rows.push(...((data as EntryRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchPlayersById(playerIds: string[]): Promise<Map<string, PlayerRow>> {
  if (playerIds.length === 0) return new Map();

  const rows: PlayerRow[] = [];
  for (const playerIdChunk of chunkValues(playerIds)) {
    const { data, error } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .in("id", playerIdChunk);

    if (error) throw new Error(`Error fetching related players: ${error.message}`);
    rows.push(...((data as PlayerRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchCommandersById(commanderIds: string[]): Promise<Map<string, CommanderRow>> {
  if (commanderIds.length === 0) return new Map();

  const rows: CommanderRow[] = [];
  for (const commanderIdChunk of chunkValues(commanderIds)) {
    const { data, error } = await supabase
      .from("commanders")
      .select("id, name")
      .in("id", commanderIdChunk);

    if (error) throw new Error(`Error fetching related commanders: ${error.message}`);
    rows.push(...((data as CommanderRow[]) ?? []));
  }

  return new Map(rows.map((row) => [row.id, row]));
}

async function fetchPlayerEventLogs(playerId: string, regionFilter: string): Promise<PlayerGameLog[]> {
  let query = supabase
    .from("regional_elo_game_event_log")
    .select(
      "game_id, game_date, tournament_name, state, round_number, round_name, table_number, seat_position, commander_name, game_result"
    )
    .eq("player_id", playerId)
    .order("game_date", { ascending: false })
    .range(0, 499);

  if (regionFilter) {
    query = query.ilike("state", regionFilter);
  }

  const { data, error } = await query;
  if (error) {
    console.error("Error fetching precomputed player event log:", error);
    return [];
  }

  const eventRows = (data as PlayerEventLogRow[]) ?? [];
  if (eventRows.length === 0) return [];

  const gameIds = Array.from(new Set(eventRows.map((row) => row.game_id)));
  const opponentRows: PlayerEventOpponentRow[] = [];
  for (const gameIdChunk of chunkArray(gameIds, 250)) {
    const { data: opponentData, error: opponentError } = await supabase
      .from("regional_elo_game_event_log")
      .select("game_id, player_id, player_name, topdeck_id, seat_position, commander_name, game_result")
      .in("game_id", gameIdChunk)
      .neq("player_id", playerId)
      .range(0, 499);

    if (opponentError) {
      console.error("Error fetching precomputed player event opponents:", opponentError);
      continue;
    }
    opponentRows.push(...((opponentData as PlayerEventOpponentRow[]) ?? []));
  }

  const opponentsByGameId = new Map<string, PlayerGameLog["opponents"]>();
  for (const row of opponentRows) {
    const existing = opponentsByGameId.get(row.game_id) ?? [];
    existing.push({
      topdeckId: row.topdeck_id,
      playerName: row.player_name ?? "Unknown",
      commanderName: row.commander_name,
      seat: (row.seat_position ?? 0) + 1,
      result: row.game_result,
    });
    opponentsByGameId.set(row.game_id, existing);
  }
  for (const opponents of opponentsByGameId.values()) {
    opponents.sort((a, b) => a.seat - b.seat);
  }

  return eventRows.map((row) => ({
    gameId: row.game_id,
    startDate: row.game_date ?? "",
    tournamentName: row.tournament_name ?? "Unknown tournament",
    state: row.state,
    roundLabel: toEventRoundLabel(row),
    tableLabel: row.table_number !== null ? `Table ${row.table_number}` : "Bracket",
    seat: (row.seat_position ?? 0) + 1,
    result: row.game_result,
    commanderName: row.commander_name,
    opponents: opponentsByGameId.get(row.game_id) ?? [],
  }));
}

export default async function RegionalPlayerPage({
  params,
  searchParams,
}: {
  params: Promise<{ topdeckId: string }> | { topdeckId: string };
  searchParams?:
    | Promise<{ region?: string | string[] }>
    | { region?: string | string[] };
}) {
  const resolvedParams = await Promise.resolve(params);
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const topdeckId = resolvedParams.topdeckId;
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim().toUpperCase();
  const regionFilter = requestedRegion === "ALL" ? "" : requestedRegion;

  const player = await fetchPlayer(topdeckId);
  if (!player) {
    return (
      <main className="container mx-auto px-4 py-10">
        <p className="text-sm text-muted-foreground">No player found for TopDeck ID {topdeckId}.</p>
      </main>
    );
  }

  const [globalSnapshot, globalEloRank, regionalRanks, entries, activeCommander] = await Promise.all([
    fetchGlobalSnapshot(topdeckId),
    fetchGlobalEloRank(player.id),
    fetchRegionalRanks(player.id),
    fetchEntries(player.id),
    fetchActiveCommander(player.id, topdeckId, player.name),
  ]);
  const homeRegion = globalEloRank?.primary_region_key ?? regionalRanks[0]?.region_key ?? null;
  const homeCountry =
    globalEloRank?.primary_country_key ??
    (homeRegion ? inferCountryForRegion(homeRegion) : null);
  const regionalRankRows = regionalRanks.map((row) => ({
    ...row,
    country_key: row.country_key ?? inferCountryForRegion(row.region_key) ?? "UNKNOWN",
  }));
  const selectedRegion = regionFilter || homeRegion || "";
  const regionalRank = await fetchRegionalRank(player.id, selectedRegion);
  const activeRank = regionFilter ? regionalRank : globalEloRank;
  let playerLogs = await fetchPlayerEventLogs(player.id, "");

  if (playerLogs.length === 0) {
    const entryIds = entries.map((row) => row.id);
    const { participants, games, allParticipants } = await fetchGamesAndParticipants(entryIds);

    const gamesById = new Map(games.map((row) => [row.id, row]));
    const entryById = new Map(entries.map((row) => [row.id, row]));
    const tournamentIds = Array.from(new Set(games.map((row) => row.tournament_id)));
    const tournamentsById = await fetchTournaments(tournamentIds);

    const playerParticipants = participants.filter((participant) => {
      if (!gamesById.has(participant.game_id)) return false;
      return true;
    });
    const playerGameIds = Array.from(new Set(playerParticipants.map((row) => row.game_id)));
    const relatedParticipants = allParticipants.filter((row) => playerGameIds.includes(row.game_id));
    const relatedEntryIds = Array.from(new Set(relatedParticipants.map((row) => row.entry_id)));
    const relatedEntriesById = await fetchEntriesById(relatedEntryIds);
    const relatedPlayerIds = Array.from(
      new Set(Array.from(relatedEntriesById.values()).map((row) => row.player_id))
    );
    const relatedCommanderIds = Array.from(
      new Set(
        Array.from(relatedEntriesById.values())
          .map((row) => row.commander_id)
          .filter((value): value is string => Boolean(value))
      )
    );
    const playersById = await fetchPlayersById(relatedPlayerIds);
    const commandersById = await fetchCommandersById(relatedCommanderIds);

    playerLogs = playerParticipants
      .map((participant) => {
        const game = gamesById.get(participant.game_id);
        const playerEntry = entryById.get(participant.entry_id);
        if (!game || !playerEntry) return null;

        const tournament = tournamentsById.get(game.tournament_id);
        const commanderName = playerEntry.commander_id
          ? commandersById.get(playerEntry.commander_id)?.name ?? null
          : null;
        const pod = relatedParticipants
          .filter((row) => row.game_id === participant.game_id && row.entry_id !== participant.entry_id)
          .map((row) => {
            const opponentEntry = relatedEntriesById.get(row.entry_id);
            const opponentPlayer = opponentEntry ? playersById.get(opponentEntry.player_id) : null;
            const opponentCommander = opponentEntry?.commander_id
              ? commandersById.get(opponentEntry.commander_id)?.name ?? null
              : null;

            return {
              topdeckId: opponentPlayer?.topdeck_id ?? null,
              playerName: opponentPlayer?.name ?? "Unknown",
              commanderName: opponentCommander,
              seat: row.seat_position + 1,
              result: row.result,
            };
          })
          .sort((a, b) => a.seat - b.seat);

        return {
          gameId: participant.game_id,
          startDate: tournament?.start_date ?? "",
          tournamentName: tournament?.name ?? "Unknown tournament",
          state: tournament?.state ?? null,
          roundLabel: toRoundLabel(game),
          tableLabel: game.table_number !== null ? `Table ${game.table_number}` : "Bracket",
          seat: participant.seat_position + 1,
          result: participant.result,
          commanderName,
          opponents: pod,
        } satisfies PlayerGameLog;
      })
      .filter((value): value is PlayerGameLog => Boolean(value))
      .sort((a, b) => b.startDate.localeCompare(a.startDate));
  }

  const { totalGames, totalWins, totalDraws, totalLosses, seatRows, opponentRecords } = summarizePlayerLogs(playerLogs);
  const canonicalGames = globalEloRank?.games_played ?? totalGames;
  const canonicalWins = globalEloRank?.wins ?? totalWins;
  const canonicalDraws = globalEloRank?.draws ?? totalDraws;
  const canonicalLosses = globalEloRank?.losses ?? totalLosses;
  const assignmentRowsByRegion = new Map<string, StateAssignmentRow>();
  const historicalRegionKeys = new Set<string>();
  for (const row of regionalRankRows) {
    const regionKey = row.region_key ?? "";
    if (!regionKey) continue;
    assignmentRowsByRegion.set(regionKey, {
      country_key: row.country_key ?? inferCountryForRegion(regionKey) ?? "UNKNOWN",
      region_key: regionKey,
      rank: row.rank,
      rating: row.rating,
      games_played: row.games_played,
      wins: row.wins,
      draws: row.draws,
      losses: row.losses,
    });
  }
  for (const log of playerLogs) {
    const regionKey = (log.state ?? "").trim().toUpperCase() || "UNKNOWN";
    const existing = assignmentRowsByRegion.get(regionKey);
    const current =
      existing && !historicalRegionKeys.has(regionKey)
        ? {
            ...existing,
            games_played: 0,
            wins: 0,
            draws: 0,
            losses: 0,
          }
        : existing ?? {
            country_key: inferCountryForRegion(regionKey) ?? "UNKNOWN",
            region_key: regionKey,
            rank: null,
            rating: null,
            games_played: 0,
            wins: 0,
            draws: 0,
            losses: 0,
          };

    historicalRegionKeys.add(regionKey);
    current.games_played += 1;
    if (log.result === "win") {
      current.wins += 1;
    } else if (log.result === "draw") {
      current.draws += 1;
    } else if (log.result === "loss") {
      current.losses += 1;
    }
    assignmentRowsByRegion.set(regionKey, current);
  }
  const stateAssignmentRows = Array.from(assignmentRowsByRegion.values()).sort((a, b) => {
    if (a.region_key === homeRegion) return -1;
    if (b.region_key === homeRegion) return 1;
    if (a.country_key === "UNKNOWN" && b.country_key !== "UNKNOWN") return 1;
    if (b.country_key === "UNKNOWN" && a.country_key !== "UNKNOWN") return -1;
    if (a.country_key !== b.country_key) return a.country_key.localeCompare(b.country_key);
    if (a.region_key === "UNKNOWN" && b.region_key !== "UNKNOWN") return 1;
    if (b.region_key === "UNKNOWN" && a.region_key !== "UNKNOWN") return -1;
    if (b.games_played !== a.games_played) return b.games_played - a.games_played;
    return a.region_key.localeCompare(b.region_key);
  });
  const countryAssignmentRows = Array.from(new Set(stateAssignmentRows.map((row) => row.country_key))).sort((a, b) => {
    if (a === homeCountry) return -1;
    if (b === homeCountry) return 1;
    if (a === "UNKNOWN") return 1;
    if (b === "UNKNOWN") return -1;
    return a.localeCompare(b);
  });
  const commanderRows = Array.from(
    playerLogs.reduce(
      (rows, log) => {
        const commander = log.commanderName?.trim() || "Unknown Commander";
        const current = rows.get(commander) ?? {
          commander,
          games: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          latestDate: "",
        };
        current.games += 1;
        if (log.result === "win") {
          current.wins += 1;
        } else if (log.result === "draw") {
          current.draws += 1;
        } else if (log.result === "loss") {
          current.losses += 1;
        }
        if (log.startDate > current.latestDate) {
          current.latestDate = log.startDate;
        }
        rows.set(commander, current);
        return rows;
      },
      new Map<
        string,
        {
          commander: string;
          games: number;
          wins: number;
          draws: number;
          losses: number;
          latestDate: string;
        }
      >()
    ).values()
  ).sort((a, b) => {
    if (a.commander === "Unknown Commander") return 1;
    if (b.commander === "Unknown Commander") return -1;
    if (b.games !== a.games) return b.games - a.games;
    if (b.latestDate !== a.latestDate) return b.latestDate.localeCompare(a.latestDate);
    return a.commander.localeCompare(b.commander);
  });
  const topdeckProfileHref = buildTopdeckProfileHref(topdeckId);
  const backHref = regionFilter
    ? `/regional-elo?scope=state&region=${encodeURIComponent(regionFilter)}`
    : "/regional-elo";

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <div className="space-y-3">
            <Link href={backHref} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to region-filtered leaderboard
            </Link>
            <p className="knd-chip">Global Elo Player Drilldown</p>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  {player.name}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Home region is assigned from recent and sustained activity. This page defaults
                  to the global view; use the region filter below to inspect a specific state slice.
                </p>
              </div>
              {topdeckProfileHref ? (
                <a
                  href={topdeckProfileHref}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary hover:text-foreground"
                >
                  Open TopDeck profile
                </a>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-8">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Home Region
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {homeRegion ?? "Unassigned"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Current Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {activeRank ? `#${activeRank.rank}` : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Global Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {globalEloRank ? `#${globalEloRank.rank}` : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  TopDeck Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {globalSnapshot ? `#${globalSnapshot.rank}` : "—"}
                </div>
                <div className="text-sm text-muted-foreground">
                  {globalSnapshot ? `${globalSnapshot.points} points` : "No global snapshot"}
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Elo
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {globalEloRank ? Math.round(globalEloRank.rating) : "—"}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Games Played
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {canonicalGames}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Record
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {canonicalWins}-{canonicalLosses}-{canonicalDraws}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Opponents
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {opponentRecords.length}
              </CardContent>
            </Card>
          </div>

          <p className="text-sm text-muted-foreground">
            Elo is global. Home region is assigned separately. The summary cards and game log below
            include all stored games across regions. The active filter only changes the highlighted
            state rank.
          </p>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Played Commanders
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Commanders from all stored games for this player, sorted by total games.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commanderRows.map((row) => {
                      const isActive = activeCommander === row.commander;
                      return (
                        <tr key={row.commander} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            <span className={isActive ? "font-semibold text-foreground" : "text-foreground"}>
                              {row.commander === "Unknown Commander" ? "Unknown" : row.commander}
                            </span>
                            {isActive ? (
                              <div className="text-[11px] text-primary">Active commander</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {commanderRows.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No commander game history found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                State Assignment
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Historical games are grouped by inferred country and region. Assigned-state rank
                data appears when available.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Country</th>
                      <th className="px-2 py-3">Region</th>
                      <th className="px-2 py-3 text-right">Rank</th>
                      <th className="px-2 py-3 text-right">Elo</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {countryAssignmentRows.flatMap((countryKey) => {
                      const rowsForCountry = stateAssignmentRows.filter((row) => row.country_key === countryKey);
                      return [
                        <tr key={`country:${countryKey}`} className="border-t border-border/60 bg-muted/20">
                          <td colSpan={6} className="px-2 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                            {countryKey === "UNKNOWN" ? "UNKNOWN country" : countryKey}
                          </td>
                        </tr>,
                        ...rowsForCountry.map((row) => {
                          const regionKey = row.region_key ?? "";
                          const isActive = regionKey === regionFilter;
                          return (
                            <tr key={`${countryKey}:${regionKey}`} className="border-t border-border/60">
                              <td className="px-2 py-3 text-muted-foreground">
                                {countryKey === "UNKNOWN" ? "UNKNOWN country" : countryKey}
                              </td>
                              <td className="px-2 py-3">
                                <Link
                                  href={`/regional-elo/player/${topdeckId}?region=${encodeURIComponent(regionKey)}`}
                                  className={
                                    isActive
                                      ? "font-semibold text-foreground hover:text-primary"
                                      : "text-foreground hover:text-primary"
                                  }
                                >
                                  {regionKey === "UNKNOWN" ? "UNKNOWN state" : regionKey}
                                </Link>
                                {regionKey === homeRegion ? (
                                  <div className="text-[11px] text-primary">Assigned state</div>
                                ) : null}
                              </td>
                              <td className="px-2 py-3 text-right font-mono text-foreground">
                                {row.rank ? `#${row.rank}` : "—"}
                              </td>
                              <td className="px-2 py-3 text-right font-mono text-foreground">
                                {row.rating ? Math.round(row.rating) : "—"}
                              </td>
                              <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                                {row.games_played}
                              </td>
                              <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                                {row.wins}-{row.losses}-{row.draws}
                              </td>
                            </tr>
                          );
                        }),
                      ];
                    })}
                    {stateAssignmentRows.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No state assignment found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Seat Distribution
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {seatRows.map((row) => (
                  <div key={row.seat} className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground">Seat {row.seat}</span>
                      <span className="font-mono text-sm text-muted-foreground">{row.games} games</span>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {row.wins}-{row.losses}-{row.draws}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Record Against Opponents
                </CardTitle>
              </CardHeader>
              <CardContent>
                <OpponentRecordsTable records={opponentRecords} />
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
