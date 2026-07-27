import { Suspense } from "react";
import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CommanderUsageRow } from "@/lib/meta-prep";
import { supabase } from "@/lib/supabase";
import { OpponentRecordsTable } from "./opponent-records-table";
import { filterPlayerLogs, summarizePlayerLogs, type PlayerGameLog } from "./player-stats";
import {
  PlayerHeader,
  PlayerHeaderSkeleton,
  PlayerProfileGrid,
  PlayerProfileGridSkeleton,
  fetchCachedPlayer,
  fetchCachedGlobalEloRank,
  fetchCachedRegionalRanks,
  fetchCachedPlayerProfileSummary,
  fetchCachedPlayerCommanderProfile,
  fetchCachedPlayerAchievements,
  fetchCachedPlayerCommanderUsageRows,
  fetchEntries,
  sortAchievementsByFinish,
  isKnownCommanderName,
} from "./player-profile-components";

export const revalidate = 86400; // 24 hours
export const dynamicParams = true;

const SUPABASE_PAGE_SIZE = 1000;
const SUPABASE_IN_CHUNK_SIZE = 100;
const ACHIEVEMENTS_PAGE_SIZE = 10;

export async function generateStaticParams() {
  try {
    const { data, error } = await supabase
      .from("global_elo_active_leaderboard")
      .select("topdeck_id, rank")
      .eq("region_type", "global")
      .eq("region_key", "ALL")
      .order("rank", { ascending: true })
      .limit(500);

    if (error) {
      console.warn("generateStaticParams: Failed to fetch leaderboard data", error);
      return [];
    }

    return (data ?? [])
      .filter((row): row is { topdeck_id: string; rank: number } => Boolean(row?.topdeck_id))
      .map((row) => ({ topdeckId: String(row.topdeck_id) }));
  } catch (err) {
    console.warn("generateStaticParams: Unexpected error during fetch", err);
    return [];
  }
}

export type PlayerRow = {
  id: string;
  name: string;
  topdeck_id: string;
};

export type PlayerCommanderUsageRow = CommanderUsageRow & {
  tournament_name: string | null;
  tournament_topdeck_tid: string | null;
};

export type EntryRow = {
  id: string;
  tournament_id: string;
  player_id: string;
  commander_id: string | null;
};

export type CommanderRow = {
  id: string;
  name: string;
};

export type ParticipantRow = {
  game_id: string;
  entry_id: string;
  seat_position: number;
  result: string;
};

export type GameRow = {
  id: string;
  tournament_id: string;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  is_draw: boolean;
  winner_id: string | null;
};

export type TournamentRow = {
  id: string;
  name: string;
  start_date: string;
  state: string | null;
  player_count: number | null;
};

export type LeaderboardRankRow = {
  player_id?: string;
  topdeck_id?: string | null;
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
  last_game_date?: string | null;
  topdeck_elo?: number | null;
  topdeck_elo_rank?: number | null;
};

export type StateAssignmentRow = {
  country_key: string;
  region_key: string;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

export type PlayerProfileSummaryRow = {
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  home_country_key: string | null;
  home_region_key: string | null;
  state_assignments: StateAssignmentRow[] | null;
};

export type GlobalSnapshotRow = {
  rank: number;
  points: number;
  tournaments: number | null;
  gamesPlayed: number | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
};

export type PlayerTournamentEntryRow = {
  final_standing: number | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  decklist_url: string | null;
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
        name: string | null;
        start_date: string | null;
        player_count: number | null;
        topdeck_tid: string | null;
      }
    | Array<{
        name: string | null;
        start_date: string | null;
        player_count: number | null;
        topdeck_tid: string | null;
      }>
    | null;
};

export type PlayerAchievementRow = {
  tournamentName: string;
  tournamentUrl: string | null;
  startDate: string | null;
  playerCount: number | null;
  placement: number | null;
  finishRatio: number | null;
  commanderName: string | null;
  decklistUrl: string | null;
  wins: number;
  draws: number;
  losses: number;
  recordGames: number;
};

export type PlayerCommanderProfileRow = {
  active_commander: string | null;
  latest_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
};

export type PlayerEventLogRow = {
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

export type PlayerEventOpponentRow = {
  game_id: string;
  player_id: string;
  player_name: string | null;
  topdeck_id: string | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
};

function toRoundLabel(game: GameRow) {
  if (game.round_name) return game.round_name;
  if (game.round_number !== null) return `Round ${game.round_number}`;
  return "Bracket";
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

function readPositiveIntParam(
  params:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined,
  key: string,
  fallback = 1
) {
  if (!params) return fallback;
  const rawValue =
    typeof (params as URLSearchParams).get === "function"
      ? (params as URLSearchParams).get(key)
      : (params as Record<string, string | string[] | undefined>)[key];
  const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function readStringParam(
  params:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined,
  key: string
) {
  if (!params) return "";
  const rawValue =
    typeof (params as URLSearchParams).get === "function"
      ? (params as URLSearchParams).get(key)
      : (params as Record<string, string | string[] | undefined>)[key];
  const value = Array.isArray(rawValue) ? rawValue[0] : rawValue;
  return (value ?? "").trim();
}

function buildPlayerProfileHref(
  topdeckId: string,
  regionFilter: string,
  achievementsPage: number,
  achievementTournamentSearch = "",
  achievementCommanderSearch = "",
  achievementSort: AchievementSort = "best",
  achievementDateFrom = "",
  achievementDateTo = "",
  eloOnly = false
) {
  const params = new URLSearchParams();
  if (regionFilter) params.set("region", regionFilter);
  if (achievementTournamentSearch) params.set("achievementTournament", achievementTournamentSearch);
  if (achievementCommanderSearch) params.set("achievementCommander", achievementCommanderSearch);
  if (achievementSort && achievementSort !== "best") {
    params.set("achievementSort", achievementSort);
  }
  if (achievementDateFrom) params.set("achievementDateFrom", achievementDateFrom);
  if (achievementDateTo) params.set("achievementDateTo", achievementDateTo);
  if (achievementsPage > 1) params.set("achievementsPage", String(achievementsPage));
  if (eloOnly) params.set("eloOnly", "true");
  const query = params.toString();
  return `/regional-elo/player/${topdeckId}${query ? `?${query}` : ""}`;
}

type AchievementSort = "recent" | "best";

function normalizeAchievementSort(value: string): AchievementSort {
  return value === "recent" ? "recent" : "best";
}

function buildTopdeckTournamentUrl(tournamentSlug: string | null | undefined) {
  return tournamentSlug ? `https://topdeck.gg/bracket/${tournamentSlug}` : null;
}

function formatShortDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatPct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatPlacementRatio(placement: number | null, playerCount: number | null) {
  if (!placement || !playerCount) return "—";
  return `${placement} / ${playerCount}`;
}

function achievementTournamentKey(tournamentName: string | null | undefined, startDate: string | null | undefined) {
  return `${tournamentName ?? "Unknown tournament"}:${(startDate ?? "").slice(0, 10)}`;
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

async function buildPlayerLogsFromRawHistory(entries: EntryRow[]): Promise<PlayerGameLog[]> {
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

  return playerParticipants
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
        tournamentPlayerCount: tournament?.player_count ?? null,
        commanderName,
        opponents: pod,
      } satisfies PlayerGameLog;
    })
    .filter((value) => value !== null)
    .map((value) => value as PlayerGameLog)
    .sort((a, b) => b.startDate.localeCompare(a.startDate));
}

async function fetchTournaments(tournamentIds: string[]): Promise<Map<string, TournamentRow>> {
  if (tournamentIds.length === 0) return new Map();

  const rows: TournamentRow[] = [];
  for (const tournamentIdChunk of chunkValues(tournamentIds)) {
    const { data, error } = await supabase
      .from("tournaments")
      .select("id, name, start_date, state, player_count")
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

export default async function RegionalPlayerPage({
  params,
  searchParams,
}: {
  params: Promise<{ topdeckId: string }> | { topdeckId: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const resolvedParams = await Promise.resolve(params);
  const topdeckId = resolvedParams.topdeckId;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <Suspense fallback={<PlayerHeaderSkeleton />}>
            <PlayerHeader topdeckId={topdeckId} />
          </Suspense>

          <Suspense fallback={<PlayerProfileBodySkeleton />}>
            <PlayerProfileBodyWrapper
              topdeckId={topdeckId}
              searchParams={searchParams}
            />
          </Suspense>
        </div>
      </main>
    </div>
  );
}

async function PlayerProfileBodyWrapper({
  topdeckId,
  searchParams,
}: {
  topdeckId: string;
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const player = await fetchCachedPlayer(topdeckId);
  if (!player) {
    return (
      <p className="text-sm text-muted-foreground">No player found for TopDeck ID {topdeckId}.</p>
    );
  }

  const resolvedSearchParams = await Promise.resolve(searchParams);
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim().toUpperCase();
  const regionFilter = requestedRegion === "ALL" ? "" : requestedRegion;

  return (
    <>
      <Suspense fallback={<PlayerProfileGridSkeleton />}>
        <PlayerProfileGrid
          topdeckId={topdeckId}
          player={player}
          regionFilter={regionFilter}
        />
      </Suspense>

      <PlayerProfileBody
        topdeckId={topdeckId}
        player={player}
        searchParams={searchParams}
      />
    </>
  );
}



export async function PlayerProfileBody({
  topdeckId,
  player,
  searchParams,
}: {
  topdeckId: string;
  player: PlayerRow;
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim().toUpperCase();
  const regionFilter = requestedRegion === "ALL" ? "" : requestedRegion;
  const requestedAchievementsPage = readPositiveIntParam(resolvedSearchParams, "achievementsPage");
  const achievementTournamentSearch = readStringParam(resolvedSearchParams, "achievementTournament");
  const achievementCommanderSearch = readStringParam(resolvedSearchParams, "achievementCommander");
  const achievementSort = normalizeAchievementSort(
    readStringParam(resolvedSearchParams, "achievementSort")
  );
  const achievementDateFrom = readStringParam(resolvedSearchParams, "achievementDateFrom");
  const achievementDateTo = readStringParam(resolvedSearchParams, "achievementDateTo");
  const eloOnly = readStringParam(resolvedSearchParams, "eloOnly") === "true";
  const backHref = regionFilter
    ? `/regional-elo?scope=state&region=${encodeURIComponent(regionFilter)}`
    : "/regional-elo";

  const [
    globalEloRank,
    regionalRanks,
    profileSummary,
    commanderProfile,
    commanderUsageRows,
    fetchedAchievementRows,
    rawEntries,
  ] = await Promise.all([
    fetchCachedGlobalEloRank(player.id),
    fetchCachedRegionalRanks(player.id),
    fetchCachedPlayerProfileSummary(player.id),
    fetchCachedPlayerCommanderProfile(topdeckId),
    fetchCachedPlayerCommanderUsageRows(player.id, topdeckId, player.name),
    fetchCachedPlayerAchievements(player.id, topdeckId),
    fetchEntries(player.id),
  ]);

  const activeCommander = commanderProfile?.active_commander ?? null;

  const allPlayerLogs: PlayerGameLog[] = await buildPlayerLogsFromRawHistory(rawEntries);
  const playerLogs = filterPlayerLogs(allPlayerLogs, eloOnly);
  const {
    totalGames,
    totalWins,
    totalDraws,
    totalLosses,
    seatRows,
    opponentRecords,
    commanderRecords,
    bestOpponentMatchup,
    worstOpponentMatchup,
    bestCommanderMatchup,
    worstCommanderMatchup,
  } = summarizePlayerLogs(playerLogs, topdeckId);
  const achievementResultByTournament = playerLogs.reduce(
    (results, log) => {
      const key = achievementTournamentKey(log.tournamentName, log.startDate);
      const current = results.get(key) ?? { wins: 0, draws: 0, losses: 0, games: 0 };
      current.games += 1;
      if (log.result === "win") {
        current.wins += 1;
      } else if (log.result === "draw") {
        current.draws += 1;
      } else if (log.result === "loss") {
        current.losses += 1;
      }
      results.set(key, current);
      return results;
    },
    new Map<string, { wins: number; draws: number; losses: number; games: number }>()
  );
  const allAchievementRows = fetchedAchievementRows
    .map((row: PlayerAchievementRow) => {
      const gameResults = achievementResultByTournament.get(
        achievementTournamentKey(row.tournamentName, row.startDate)
      );
      if (!gameResults?.games) return eloOnly ? null : row;
      return {
        ...row,
        wins: gameResults.wins,
        draws: gameResults.draws,
        losses: gameResults.losses,
        recordGames: gameResults.games,
      };
    })
    .filter((row): row is PlayerAchievementRow => Boolean(row && row.recordGames > 0));

  const normalizedAchievementTournamentSearch = achievementTournamentSearch.toLocaleLowerCase();
  const normalizedAchievementCommanderSearch = achievementCommanderSearch.toLocaleLowerCase();
  const filteredAchievementRows = allAchievementRows.filter((row: PlayerAchievementRow) => {
    const matchesTournament =
      !normalizedAchievementTournamentSearch ||
      row.tournamentName.toLocaleLowerCase().includes(normalizedAchievementTournamentSearch);
    const matchesCommander =
      !normalizedAchievementCommanderSearch ||
      (row.commanderName ?? "Unknown").toLocaleLowerCase().includes(normalizedAchievementCommanderSearch);
    const rowDate = (row.startDate ?? "").slice(0, 10);
    const matchesFrom = !achievementDateFrom || (rowDate && rowDate >= achievementDateFrom);
    const matchesTo = !achievementDateTo || (rowDate && rowDate <= achievementDateTo);
    return matchesTournament && matchesCommander && matchesFrom && matchesTo;
  });

  const achievementRows =
    achievementSort === "best"
      ? sortAchievementsByFinish(filteredAchievementRows)
      : filteredAchievementRows;
  const achievementPageCount = Math.max(1, Math.ceil(achievementRows.length / ACHIEVEMENTS_PAGE_SIZE));
  const achievementPage = Math.min(requestedAchievementsPage, achievementPageCount);
  const visibleAchievementRows = achievementRows.slice(
    (achievementPage - 1) * ACHIEVEMENTS_PAGE_SIZE,
    achievementPage * ACHIEVEMENTS_PAGE_SIZE
  );
  const assignmentRowsByRegion = new Map<string, StateAssignmentRow>();
  if (profileSummary?.state_assignments?.length) {
    for (const row of profileSummary.state_assignments) {
      assignmentRowsByRegion.set(row.region_key, row);
    }
  }
  const derivedHomeRegion =
    Array.from(assignmentRowsByRegion.values())
      .filter((row) => row.region_key !== "UNKNOWN")
      .sort((a, b) => {
        if (b.games_played !== a.games_played) return b.games_played - a.games_played;
        return a.region_key.localeCompare(b.region_key);
      })[0]?.region_key ?? null;
  const homeRegion = profileSummary?.home_region_key ?? globalEloRank?.primary_region_key ?? regionalRanks[0]?.region_key ?? derivedHomeRegion;
  const stateAssignmentRows = Array.from(assignmentRowsByRegion.values()).sort((a: StateAssignmentRow, b: StateAssignmentRow) => {
    const aCountry = a.country_key ?? "UNKNOWN";
    const bCountry = b.country_key ?? "UNKNOWN";
    const aRegion = a.region_key ?? "UNKNOWN";
    const bRegion = b.region_key ?? "UNKNOWN";

    if (aRegion === homeRegion) return -1;
    if (bRegion === homeRegion) return 1;
    if (aCountry === "UNKNOWN" && bCountry !== "UNKNOWN") return 1;
    if (bCountry === "UNKNOWN" && aCountry !== "UNKNOWN") return -1;
    if (aCountry !== bCountry) return aCountry.localeCompare(bCountry);
    if (aRegion === "UNKNOWN" && bRegion !== "UNKNOWN") return 1;
    if (bRegion === "UNKNOWN" && aRegion !== "UNKNOWN") return -1;
    if (b.games_played !== a.games_played) return b.games_played - a.games_played;
    return aRegion.localeCompare(bRegion);
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
    if (b.latestDate !== a.latestDate) return b.latestDate.localeCompare(a.latestDate);
    if (b.games !== a.games) return b.games - a.games;
    return a.commander.localeCompare(b.commander);
  });
  const latestDecklistByCommander = new Map<string, { date: string; url: string }>();
  const latestTournamentByCommander = new Map<
    string,
    { date: string; name: string; url: string | null }
  >();
  for (const row of commanderUsageRows) {
    const commanderName = row.commander_name;
    if (!isKnownCommanderName(commanderName) || !commanderName || !row.start_date) continue;
    const url = row.decklist_url || row.topdeck_decklist_url;
    const existingDecklist = latestDecklistByCommander.get(commanderName);
    if (url && (!existingDecklist || row.start_date > existingDecklist.date)) {
      latestDecklistByCommander.set(commanderName, { date: row.start_date, url });
    }
    const tournamentName = row.tournament_name || "Unknown tournament";
    const existingTournament = latestTournamentByCommander.get(commanderName);
    if (!existingTournament || row.start_date > existingTournament.date) {
      latestTournamentByCommander.set(commanderName, {
        date: row.start_date,
        name: tournamentName,
        url: buildTopdeckTournamentUrl(row.tournament_topdeck_tid),
      });
    }
  }
  if (activeCommander) {
    if (
      commanderProfile?.latest_decklist_url &&
      commanderProfile.latest_tournament_date &&
      !latestDecklistByCommander.has(activeCommander)
    ) {
      latestDecklistByCommander.set(activeCommander, {
        date: commanderProfile.latest_tournament_date,
        url: commanderProfile.latest_decklist_url,
      });
    }
    if (
      commanderProfile?.latest_tournament_date &&
      !latestTournamentByCommander.has(activeCommander)
    ) {
      latestTournamentByCommander.set(activeCommander, {
        date: commanderProfile.latest_tournament_date,
        name: commanderProfile.latest_tournament_name || "Unknown tournament",
        url: buildTopdeckTournamentUrl(commanderProfile.latest_tournament_topdeck_tid),
      });
    }
  }
  const eloToggleHref = buildPlayerProfileHref(
    topdeckId,
    regionFilter,
    1,
    achievementTournamentSearch,
    achievementCommanderSearch,
    achievementSort,
    achievementDateFrom,
    achievementDateTo,
    !eloOnly
  );
  return (
    <>
      <Link href={backHref} className="-mt-6 block text-sm text-muted-foreground hover:text-foreground">
        ← Back to region leaderboard
      </Link>

      <Card className="knd-panel">
        <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
          <div>
            <div className="text-sm font-medium text-foreground">Game filter</div>
            <p className="text-xs text-muted-foreground">
              Aggregate W-L-D stats can be limited to Elo-worthy events with 30+ players; Elo
              rankings are unchanged.
            </p>
          </div>
          <Link
            href={eloToggleHref}
            role="switch"
            aria-checked={eloOnly}
            className="min-h-11 rounded-md border border-border/70 px-3 py-2 text-sm text-foreground hover:border-primary/40 hover:text-primary"
          >
            {eloOnly ? "Showing 30+ player games" : "Show 30+ player games only"}
          </Link>
        </CardContent>
      </Card>

      <Card className="knd-panel">
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
            Played Commanders
          </CardTitle>
              <p className="text-xs text-muted-foreground">
                Commanders from all stored games for this player, sorted by last played.
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3">Last Played</th>
                      <th className="px-2 py-3 text-right">Games</th>
                      <th className="px-2 py-3 text-right hidden sm:table-cell">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commanderRows.map((row) => {
                      const isActive = activeCommander === row.commander;
                      const decklistUrl =
                        row.commander === "Unknown Commander"
                          ? null
                          : latestDecklistByCommander.get(row.commander)?.url ?? null;
                      const latestTournament =
                        row.commander === "Unknown Commander"
                          ? null
                          : latestTournamentByCommander.get(row.commander) ?? null;
                      const commanderLabel = row.commander === "Unknown Commander" ? "Unknown" : row.commander;
                      return (
                        <tr key={row.commander} className="border-t border-border/60">
                          <td className="px-2 py-3">
                            {decklistUrl ? (
                              <a
                                href={decklistUrl}
                                target="_blank"
                                rel="noreferrer"
                                className={
                                  isActive
                                    ? "font-semibold text-foreground hover:text-primary"
                                    : "text-foreground hover:text-primary"
                                }
                              >
                                {commanderLabel}
                              </a>
                            ) : (
                              <span className={isActive ? "font-semibold text-foreground" : "text-foreground"}>
                                {commanderLabel}
                              </span>
                            )}
                            {isActive ? (
                              <div className="text-[11px] text-primary">Active commander</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-muted-foreground">
                            {latestTournament ? (
                              latestTournament.url ? (
                                <a
                                  href={latestTournament.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="hover:text-primary"
                                >
                                  {formatShortDate(latestTournament.date)}
                                  {/* Tournament names blow out the column width on phones */}
                                  <span className="hidden sm:inline"> | {latestTournament.name}</span>
                                </a>
                              ) : (
                                <span>
                                  {formatShortDate(latestTournament.date)}
                                  <span className="hidden sm:inline"> | {latestTournament.name}</span>
                                </span>
                              )
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground hidden sm:table-cell">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {commanderRows.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-2 py-6 text-center text-sm text-muted-foreground">
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
                  Played Regions
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Historical games are grouped by inferred country and region.
                </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-3">Country</th>
                        <th className="px-2 py-3">State</th>
                        <th className="px-2 py-3 text-right">Games</th>
                        <th className="px-2 py-3 text-right hidden sm:table-cell">W-L-D</th>
                      </tr>
                  </thead>
                  <tbody>
                    {stateAssignmentRows.map((row) => {
                      const countryKey = row.country_key;
                      const regionKey = row.region_key ?? "";
                      const isActive = regionKey === regionFilter;
                      return (
                        <tr key={`${countryKey}:${regionKey}`} className="border-t border-border/60">
                          <td className="px-2 py-3 text-muted-foreground">
                            {countryKey === "UNKNOWN" ? "UNKNOWN" : countryKey}
                          </td>
                          <td className="px-2 py-3">
                            <Link
                              href={buildPlayerProfileHref(topdeckId, regionKey, 1, "", "", "best", "", "", eloOnly)}
                              className={
                                isActive
                                  ? "font-semibold text-foreground hover:text-primary"
                                  : "text-foreground hover:text-primary"
                              }
                            >
                              {regionKey === "UNKNOWN" ? "UNKNOWN" : regionKey}
                            </Link>
                            {regionKey === homeRegion ? (
                              <div className="text-[11px] text-primary">Home region</div>
                            ) : null}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.games_played}
                          </td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground hidden sm:table-cell">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      );
                    })}
                    {stateAssignmentRows.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No state assignment found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[360px_1fr_1fr]">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Seat Distribution
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Score = (wins + 0.2 × draws) / games
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-border/60 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">Overall</span>
                    <span className="font-mono text-sm text-muted-foreground">{totalGames} games</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-4 text-sm text-muted-foreground">
                    <span>
                      {totalWins}-{totalLosses}-{totalDraws}
                    </span>
                    <span className="font-mono">
                      Score: {formatPct((totalWins + totalDraws * 0.2) / Math.max(totalGames, 1))}
                    </span>
                  </div>
                </div>
                {seatRows.map((row) => (
                  <div key={row.seat} className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground">Seat {row.seat}</span>
                      <span className="font-mono text-sm text-muted-foreground">{row.games} games</span>
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-4 text-sm text-muted-foreground">
                      <span>
                        {row.wins}-{row.losses}-{row.draws}
                      </span>
                      <span className="font-mono">
                        Score: {formatPct((row.wins + row.draws * 0.2) / Math.max(row.games, 1))}
                      </span>
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
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Best Matchup</div>
                    {bestOpponentMatchup ? (
                      <>
                        <div className="mt-2 font-medium text-foreground">
                          {bestOpponentMatchup.href ? (
                            <Link href={bestOpponentMatchup.href} className="hover:text-primary">
                              {bestOpponentMatchup.label}
                            </Link>
                          ) : (
                            bestOpponentMatchup.label
                          )}
                        </div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {bestOpponentMatchup.wins}-{bestOpponentMatchup.losses}-{bestOpponentMatchup.draws} in{" "}
                          {bestOpponentMatchup.games} games
                        </div>
                        <div className="mt-1 text-sm text-primary">
                          Adjusted score: {formatPct(bestOpponentMatchup.posteriorScore)}
                        </div>
                      </>
                    ) : (
                      <div className="mt-2 text-sm text-muted-foreground">No opponent matchup data.</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Worst Matchup</div>
                    {worstOpponentMatchup ? (
                      <>
                        <div className="mt-2 font-medium text-foreground">
                          {worstOpponentMatchup.href ? (
                            <Link href={worstOpponentMatchup.href} className="hover:text-primary">
                              {worstOpponentMatchup.label}
                            </Link>
                          ) : (
                            worstOpponentMatchup.label
                          )}
                        </div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {worstOpponentMatchup.wins}-{worstOpponentMatchup.losses}-{worstOpponentMatchup.draws} in{" "}
                          {worstOpponentMatchup.games} games
                        </div>
                        <div className="mt-1 text-sm text-[hsl(var(--destructive))]">
                          Adjusted score: {formatPct(worstOpponentMatchup.posteriorScore)}
                        </div>
                      </>
                    ) : (
                      <div className="mt-2 text-sm text-muted-foreground">No opponent matchup data.</div>
                    )}
                  </div>
                </div>
                <OpponentRecordsTable records={opponentRecords} playerTopdeckId={topdeckId} />
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  Record Against Commanders
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Best Matchup</div>
                    {bestCommanderMatchup ? (
                      <>
                        <div className="mt-2 font-medium text-foreground">{bestCommanderMatchup.label}</div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {bestCommanderMatchup.wins}-{bestCommanderMatchup.losses}-{bestCommanderMatchup.draws} in{" "}
                          {bestCommanderMatchup.games} games
                        </div>
                        <div className="mt-1 text-sm text-primary">
                          Adjusted score: {formatPct(bestCommanderMatchup.posteriorScore)}
                        </div>
                      </>
                    ) : (
                      <div className="mt-2 text-sm text-muted-foreground">No commander matchup data.</div>
                    )}
                  </div>
                  <div className="rounded-lg border border-border/60 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Worst Matchup</div>
                    {worstCommanderMatchup ? (
                      <>
                        <div className="mt-2 font-medium text-foreground">{worstCommanderMatchup.label}</div>
                        <div className="mt-1 text-sm text-muted-foreground">
                          {worstCommanderMatchup.wins}-{worstCommanderMatchup.losses}-{worstCommanderMatchup.draws} in{" "}
                          {worstCommanderMatchup.games} games
                        </div>
                        <div className="mt-1 text-sm text-[hsl(var(--destructive))]">
                          Adjusted score: {formatPct(worstCommanderMatchup.posteriorScore)}
                        </div>
                      </>
                    ) : (
                      <div className="mt-2 text-sm text-muted-foreground">No commander matchup data.</div>
                    )}
                  </div>
                </div>
                <OpponentRecordsTable
                  records={commanderRecords}
                  entityLabel="Commander"
                  emptyLabel="No commander records found."
                />
              </CardContent>
            </Card>
          </div>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Achievements
              </CardTitle>
              <p className="text-xs text-muted-foreground">Tournament finishes</p>
            </CardHeader>
            <CardContent>
              <form method="get" className="mb-4 grid gap-3 md:grid-cols-[1fr_1fr_auto_auto_auto_auto_auto]">
                {regionFilter ? <input type="hidden" name="region" value={regionFilter} /> : null}
                {eloOnly ? <input type="hidden" name="eloOnly" value="true" /> : null}
                <label className="space-y-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Tournament
                  <input
                    type="search"
                    name="achievementTournament"
                    defaultValue={achievementTournamentSearch}
                    placeholder="Search tournaments"
                    className="mt-1 w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"
                  />
                </label>
                <label className="space-y-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Commander
                  <input
                    type="search"
                    name="achievementCommander"
                    defaultValue={achievementCommanderSearch}
                    placeholder="Search commanders"
                    className="mt-1 w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-primary/60"
                  />
                </label>
                <label className="space-y-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  From
                  <input
                    type="date"
                    name="achievementDateFrom"
                    defaultValue={achievementDateFrom}
                    className="mt-1 w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none transition-colors focus:border-primary/60"
                  />
                </label>
                <label className="space-y-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  To
                  <input
                    type="date"
                    name="achievementDateTo"
                    defaultValue={achievementDateTo}
                    className="mt-1 w-full rounded-md border border-border/70 bg-background px-3 py-2 text-sm normal-case tracking-normal text-foreground outline-none transition-colors focus:border-primary/60"
                  />
                </label>
                <button
                  type="submit"
                  className="self-end rounded-md border border-border/70 px-3 py-2 text-sm text-foreground hover:border-primary/40 hover:text-primary"
                >
                  Search
                </button>
                {achievementTournamentSearch ||
                achievementCommanderSearch ||
                achievementDateFrom ||
                achievementDateTo ||
                achievementSort !== "best" ? (
                  <Link
                    href={buildPlayerProfileHref(topdeckId, regionFilter, 1, "", "", "best", "", "", eloOnly)}
                    className="self-end rounded-md border border-border/70 px-3 py-2 text-center text-sm text-foreground hover:border-primary/40 hover:text-primary"
                  >
                    Clear
                  </Link>
                ) : null}
              </form>
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Tournament</th>
                      <th className="px-2 py-3 hidden sm:table-cell">
                        <Link
                          href={buildPlayerProfileHref(
                            topdeckId,
                            regionFilter,
                            1,
                            achievementTournamentSearch,
                            achievementCommanderSearch,
                            "recent",
                            achievementDateFrom,
                            achievementDateTo,
                            eloOnly
                          )}
                          className={achievementSort === "recent" ? "text-foreground" : "hover:text-primary"}
                        >
                          Date
                        </Link>
                      </th>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3 text-right">Finish</th>
                      <th className="px-2 py-3 text-right hidden md:table-cell">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleAchievementRows.map((row: PlayerAchievementRow, index: number) => (
                      <tr
                        key={`${row.tournamentUrl ?? row.tournamentName}:${row.startDate ?? index}`}
                        className="border-t border-border/60"
                      >
                        <td className="px-2 py-3">
                          {row.tournamentUrl ? (
                            <a
                              href={row.tournamentUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-foreground hover:text-primary line-clamp-2 max-w-[140px] sm:max-w-none"
                            >
                              {row.tournamentName}
                            </a>
                          ) : (
                            <span className="text-foreground line-clamp-2 max-w-[140px] sm:max-w-none">{row.tournamentName}</span>
                          )}
                        </td>
                        <td className="px-2 py-3 text-muted-foreground hidden sm:table-cell">
                          {formatShortDate(row.startDate)}
                        </td>
                        <td className="px-2 py-3 text-muted-foreground">
                          {row.commanderName && row.decklistUrl ? (
                            <a
                              href={row.decklistUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-foreground hover:text-primary line-clamp-1 max-w-[100px] sm:max-w-none"
                            >
                              {row.commanderName}
                            </a>
                          ) : (
                            <span className="line-clamp-1 max-w-[100px] sm:max-w-none">{row.commanderName ?? "Unknown"}</span>
                          )}
                        </td>
                        <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                          {formatPlacementRatio(row.placement, row.playerCount)}
                        </td>
                        <td className="px-2 py-3 text-right font-mono text-muted-foreground hidden md:table-cell">
                          {row.recordGames > 0 ? `${row.wins}-${row.losses}-${row.draws}` : "—"}
                        </td>
                      </tr>
                    ))}
                    {achievementRows.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-2 py-6 text-center text-sm text-muted-foreground">
                          No tournament finishes with recorded games found for this player.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
              {achievementRows.length > ACHIEVEMENTS_PAGE_SIZE ? (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-4 text-sm text-muted-foreground">
                  <span>
                    Showing {(achievementPage - 1) * ACHIEVEMENTS_PAGE_SIZE + 1}-
                    {Math.min(achievementPage * ACHIEVEMENTS_PAGE_SIZE, achievementRows.length)} of{" "}
                    {achievementRows.length}
                  </span>
                  <div className="flex items-center gap-2">
                    {achievementPage > 1 ? (
                      <Link
                        href={buildPlayerProfileHref(
                          topdeckId,
                          regionFilter,
                          achievementPage - 1,
                          achievementTournamentSearch,
                          achievementCommanderSearch,
                          achievementSort,
                          achievementDateFrom,
                          achievementDateTo,
                          eloOnly
                        )}
                        className="rounded-md border border-border/70 px-3 py-2.5 text-foreground hover:border-primary/40 hover:text-primary sm:py-1.5"
                      >
                        Previous
                      </Link>
                    ) : (
                      <span className="rounded-md border border-border/40 px-3 py-2.5 text-muted-foreground/60 sm:py-1.5">
                        Previous
                      </span>
                    )}
                    <span className="font-mono text-xs">
                      Page {achievementPage} / {achievementPageCount}
                    </span>
                    {achievementPage < achievementPageCount ? (
                      <Link
                        href={buildPlayerProfileHref(
                          topdeckId,
                          regionFilter,
                          achievementPage + 1,
                          achievementTournamentSearch,
                          achievementCommanderSearch,
                          achievementSort,
                          achievementDateFrom,
                          achievementDateTo,
                          eloOnly
                        )}
                        className="rounded-md border border-border/70 px-3 py-2.5 text-foreground hover:border-primary/40 hover:text-primary sm:py-1.5"
                      >
                        Next
                      </Link>
                    ) : (
                      <span className="rounded-md border border-border/40 px-3 py-2.5 text-muted-foreground/60 sm:py-1.5">
                        Next
                      </span>
                    )}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
    </>
  );
}

function PlayerProfileBodySkeleton() {
  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-9" aria-hidden>
        {Array.from({ length: 9 }).map((_, i) => (
          <Card key={i} className="knd-panel">
            <CardHeader>
              <div className="h-3 w-20 rounded bg-muted/40" />
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="h-7 w-16 rounded bg-muted/40" />
              <div className="h-3 w-12 rounded bg-muted/40" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div
        aria-hidden
        className="rounded-lg border border-border/40 bg-card/40 px-4 py-10 text-sm text-muted-foreground"
      >
        Loading player profile…
      </div>
      <div
        aria-hidden
        className="rounded-lg border border-border/40 bg-card/40 px-4 py-10 text-sm text-muted-foreground"
      >
        Loading commander matchups…
      </div>
      <div
        aria-hidden
        className="rounded-lg border border-border/40 bg-card/40 px-4 py-10 text-sm text-muted-foreground"
      >
        Loading achievements…
      </div>
    </>
  );
}
