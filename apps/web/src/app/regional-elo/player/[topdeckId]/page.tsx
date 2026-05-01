import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildProfiles, selectCommanderForecastRows, type CommanderUsageRow } from "@/lib/meta-prep";
import { supabase } from "@/lib/supabase";
import { fetchChampionshipLeaderboard, fetchTopDeckProfileStats } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { inferCountryForRegion } from "@/lib/region-countries";
import { OpponentRecordsTable } from "./opponent-records-table";
import { summarizePlayerLogs, type PlayerGameLog } from "./player-stats";
import { unstable_cache } from "next/cache";

export const dynamic = "force-dynamic";
const SUPABASE_PAGE_SIZE = 1000;
const SUPABASE_IN_CHUNK_SIZE = 100;
const ACTIVE_PLAYER_LOOKBACK_MONTHS = 6;
const ACHIEVEMENTS_PAGE_SIZE = 10;
const PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS = 60 * 15;

type PlayerRow = {
  id: string;
  name: string;
  topdeck_id: string;
};

type PlayerCommanderUsageRow = CommanderUsageRow & {
  tournament_name: string | null;
  tournament_topdeck_tid: string | null;
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

type StateAssignmentRow = {
  country_key: string;
  region_key: string;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

type PlayerProfileSummaryRow = {
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  home_country_key: string | null;
  home_region_key: string | null;
  state_assignments: StateAssignmentRow[] | null;
};

type GlobalSnapshotRow = {
  rank: number;
  points: number;
  tournaments: number | null;
  gamesPlayed: number | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
};

type PlayerTournamentEntryRow = {
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

type PlayerAchievementRow = {
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

function activePlayerCutoffDate() {
  const cutoff = new Date();
  cutoff.setMonth(cutoff.getMonth() - ACTIVE_PLAYER_LOOKBACK_MONTHS);
  return cutoff.toISOString().slice(0, 10);
}

function isActiveRank(row: LeaderboardRankRow | null) {
  return Boolean(row?.last_game_date && row.last_game_date >= activePlayerCutoffDate());
}

function describeSupabaseError(error: unknown) {
  if (!error) return "unknown error";
  if (error instanceof Error) return error.message;
  if (typeof error === "object") {
    const details = error as { message?: string; code?: string; details?: string; hint?: string };
    return [details.message, details.code, details.details, details.hint].filter(Boolean).join(" | ") || JSON.stringify(error);
  }
  return String(error);
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
  achievementCommanderSearch = ""
) {
  const params = new URLSearchParams();
  if (regionFilter) params.set("region", regionFilter);
  if (achievementTournamentSearch) params.set("achievementTournament", achievementTournamentSearch);
  if (achievementCommanderSearch) params.set("achievementCommander", achievementCommanderSearch);
  if (achievementsPage > 1) params.set("achievementsPage", String(achievementsPage));
  const query = params.toString();
  return `/regional-elo/player/${topdeckId}${query ? `?${query}` : ""}`;
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
  const rows: EntryRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
    const { data, error } = await supabase
      .from("tournament_entries")
      .select("id, tournament_id, player_id, commander_id")
      .eq("player_id", playerId)
      .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

    if (error) throw new Error(`Error fetching player entries: ${error.message}`);
    rows.push(...((data as EntryRow[]) ?? []));
    if (!data || data.length < SUPABASE_PAGE_SIZE) break;
  }

  return rows;
}

async function fetchActiveRankRow(
  table: "global_elo_active_leaderboard" | "regional_elo_active_leaderboard",
  regionType: "global" | "country" | "state",
  regionKey: string,
  playerId: string
): Promise<LeaderboardRankRow | null> {
  const { data, error } = await supabase
    .from(table)
    .select(
      "country_key, primary_country_key, primary_region_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date, topdeck_elo, topdeck_elo_rank"
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) return null;
  const row = (data as LeaderboardRankRow | null) ?? null;
  return row ? { ...row, rank: row.topdeck_elo_rank ?? row.rank } : null;
}

async function fetchGlobalEloRatingRow(
  table: "global_elo_ratings" | "regional_elo_ratings",
  playerId: string
): Promise<LeaderboardRankRow | null> {
  const { data, error } = await supabase
    .from(table)
    .select("rating, games_played, wins, draws, losses, last_game_date")
    .eq("region_type", "global")
    .eq("region_key", "ALL")
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) return null;
  const row = data as Omit<LeaderboardRankRow, "rank"> | null;
  return row ? { ...row, rank: 0 } : null;
}

async function fetchGlobalEloRank(playerId: string): Promise<LeaderboardRankRow | null> {
  const globalActiveRow = await fetchActiveRankRow("global_elo_active_leaderboard", "global", "ALL", playerId);
  if (globalActiveRow) {
    return globalActiveRow;
  }

  const legacyActiveRow = await fetchActiveRankRow("regional_elo_active_leaderboard", "global", "ALL", playerId);
  if (legacyActiveRow) {
    return legacyActiveRow;
  }

  const { data, error } = await supabase
    .from("global_elo_leaderboard")
    .select("primary_country_key, primary_region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
    .eq("region_type", "global")
    .eq("region_key", "ALL")
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) {
    const { data: fallbackData, error: fallbackError } = await supabase
      .from("regional_elo_leaderboard")
      .select("rank, rating, games_played, wins, draws, losses, last_game_date")
      .eq("region_type", "global")
      .eq("region_key", "ALL")
      .eq("player_id", playerId)
      .maybeSingle();

    const row =
      !fallbackError && fallbackData
        ? (fallbackData as LeaderboardRankRow)
        : await fetchGlobalEloRatingRow("regional_elo_ratings", playerId);
    return row;
  }

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchRegionalRank(playerId: string, regionKey: string): Promise<LeaderboardRankRow | null> {
  if (!regionKey) return null;
  const globalActiveRow = await fetchActiveRankRow("global_elo_active_leaderboard", "state", regionKey, playerId);
  if (globalActiveRow) {
    return globalActiveRow;
  }

  const legacyActiveRow = await fetchActiveRankRow("regional_elo_active_leaderboard", "state", regionKey, playerId);
  if (legacyActiveRow) {
    return legacyActiveRow;
  }

  const { data, error } = await supabase
    .from("global_elo_leaderboard")
    .select("country_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
    .eq("region_type", "state")
    .eq("region_key", regionKey)
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) {
    const { data: fallbackData } = await supabase
      .from("global_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
      .eq("region_type", "state")
      .eq("region_key", regionKey)
      .eq("player_id", playerId)
      .maybeSingle();

    if (fallbackData) {
      return fallbackData as LeaderboardRankRow;
    }

    const { data: legacyData } = await supabase
      .from("regional_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
      .eq("region_type", "state")
      .eq("region_key", regionKey)
      .eq("player_id", playerId)
      .maybeSingle();

    return (legacyData as LeaderboardRankRow | null) ?? null;
  }

  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchCountryRank(playerId: string, countryKey: string): Promise<LeaderboardRankRow | null> {
  if (!countryKey || countryKey === "UNKNOWN") return null;

  const globalActiveRow = await fetchActiveRankRow("global_elo_active_leaderboard", "country", countryKey, playerId);
  if (globalActiveRow) return globalActiveRow;

  const legacyActiveRow = await fetchActiveRankRow("regional_elo_active_leaderboard", "country", countryKey, playerId);
  if (legacyActiveRow) return legacyActiveRow;

  const { data, error } = await supabase
    .from("regional_elo_leaderboard")
    .select("country_key, primary_region_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
    .eq("region_type", "country")
    .eq("region_key", countryKey)
    .eq("player_id", playerId)
    .maybeSingle();

  if (error) return null;
  return (data as LeaderboardRankRow | null) ?? null;
}

async function fetchRegionalRanks(playerId: string): Promise<LeaderboardRankRow[]> {
  const { data, error } = await supabase
    .from("global_elo_leaderboard")
    .select("country_key, region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
    .eq("region_type", "state")
    .eq("player_id", playerId)
    .order("rank", { ascending: true });

  if (error) {
    const { data: fallbackData } = await supabase
      .from("global_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
      .eq("region_type", "state")
      .eq("player_id", playerId)
      .order("rank", { ascending: true });

    if (fallbackData) {
      return ((fallbackData as LeaderboardRankRow[]) ?? []).sort((a, b) => {
        if (a.rank !== b.rank) return a.rank - b.rank;
        return (a.region_key ?? "").localeCompare(b.region_key ?? "");
      });
    }

    const { data: legacyData } = await supabase
      .from("regional_elo_leaderboard")
      .select("region_key, rank, rating, games_played, wins, draws, losses, last_game_date")
      .eq("region_type", "state")
      .eq("player_id", playerId)
      .order("rank", { ascending: true });

    return ((legacyData as LeaderboardRankRow[]) ?? []).sort((a, b) => {
      if (a.rank !== b.rank) return a.rank - b.rank;
      return (a.region_key ?? "").localeCompare(b.region_key ?? "");
    });
  }

  return ((data as LeaderboardRankRow[]) ?? []).sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;
    return (a.region_key ?? "").localeCompare(b.region_key ?? "");
  });
}

function parseStateAssignments(value: unknown): StateAssignmentRow[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((row) => {
      if (!row || typeof row !== "object") return null;
      const record = row as Partial<StateAssignmentRow>;
      const regionKey = String(record.region_key ?? "").trim();
      if (!regionKey) return null;
      return {
        country_key: String(record.country_key ?? inferCountryForRegion(regionKey) ?? "UNKNOWN"),
        region_key: regionKey,
        games_played: Number(record.games_played ?? 0),
        wins: Number(record.wins ?? 0),
        draws: Number(record.draws ?? 0),
        losses: Number(record.losses ?? 0),
      };
    })
    .filter((row): row is StateAssignmentRow => Boolean(row));
}

async function fetchPlayerProfileSummary(playerId: string): Promise<PlayerProfileSummaryRow | null> {
  for (const table of ["global_elo_player_profile_summaries", "regional_elo_player_profile_summaries"]) {
    const { data, error } = await supabase
      .from(table)
      .select("games_played, wins, draws, losses, last_game_date, home_country_key, home_region_key, state_assignments")
      .eq("player_id", playerId)
      .maybeSingle();

    if (error) continue;
    const row = data as Omit<PlayerProfileSummaryRow, "state_assignments"> & { state_assignments: unknown } | null;
    if (!row) continue;
    return {
      ...row,
      state_assignments: parseStateAssignments(row.state_assignments),
    };
  }

  return null;
}

const fetchGlobalSnapshot = unstable_cache(async (topdeckId: string): Promise<GlobalSnapshotRow | null> => {
  try {
    const [leaderboard, profileStats] = await Promise.all([
      fetchChampionshipLeaderboard(),
      fetchTopDeckProfileStats(topdeckId).catch(() => null),
    ]);
    const entry = leaderboard.find((row) => row.uid === topdeckId);
    if (!entry && !profileStats) return null;
    return {
      rank: entry?.rank ?? 0,
      points: entry?.points ?? 0,
      tournaments: profileStats?.tournaments ?? null,
      gamesPlayed: profileStats?.gamesPlayed ?? null,
      wins: profileStats?.wins ?? null,
      draws: profileStats?.draws ?? null,
      losses: profileStats?.losses ?? null,
    };
  } catch {
    return null;
  }
}, ["regional-player-global-snapshot-v1"], { revalidate: 60 * 30 });

function buildTopdeckDecklistUrl(tournamentSlug: string | null | undefined, topdeckId: string) {
  return tournamentSlug ? `https://topdeck.gg/deck/${tournamentSlug}/${topdeckId}` : null;
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

function logPlayerReadSummary(event: string, details: Record<string, unknown>) {
  console.info(`[regional-player] ${event}`, details);
}

async function fetchPlayerTournamentEntries(playerId: string): Promise<PlayerTournamentEntryRow[]> {
  const rows: PlayerTournamentEntryRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
    const { data, error } = await supabase
      .from("tournament_entries")
      .select(
        "final_standing, wins, draws, losses, decklist_url, commanders(name), tournaments(name, start_date, player_count, topdeck_tid)"
      )
      .eq("player_id", playerId)
      .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

    if (error) throw new Error(`Error fetching player tournament entries: ${error.message}`);
    rows.push(...((data as PlayerTournamentEntryRow[]) ?? []));
    if (!data || data.length < SUPABASE_PAGE_SIZE) break;
  }

  logPlayerReadSummary("tournament-entries-cache-miss", {
    playerId,
    rowsReturned: rows.length,
    supabaseQueries: Math.max(1, Math.ceil(rows.length / SUPABASE_PAGE_SIZE)),
  });

  return rows;
}

function buildPlayerAchievements(
  rows: PlayerTournamentEntryRow[],
  topdeckId: string
): PlayerAchievementRow[] {
  return rows
    .map((row) => {
      const tournament = firstRelation(row.tournaments);
      const commander = firstRelation(row.commanders);
      const placement = row.final_standing ?? null;
      const playerCount = tournament?.player_count ?? null;
      const finishRatio =
        placement && playerCount && playerCount > 0 ? placement / playerCount : null;

      return {
        tournamentName: tournament?.name ?? "Unknown tournament",
        tournamentUrl: buildTopdeckTournamentUrl(tournament?.topdeck_tid),
        startDate: tournament?.start_date ?? null,
        playerCount,
        placement,
        finishRatio,
        commanderName: isKnownCommanderName(commander?.name) ? commander?.name ?? null : null,
        decklistUrl: row.decklist_url || buildTopdeckDecklistUrl(tournament?.topdeck_tid, topdeckId),
        wins: Number(row.wins ?? 0),
        draws: Number(row.draws ?? 0),
        losses: Number(row.losses ?? 0),
        recordGames: Number(row.wins ?? 0) + Number(row.draws ?? 0) + Number(row.losses ?? 0),
      };
    })
    .sort((a, b) => {
      const dateCompare = (b.startDate ?? "").localeCompare(a.startDate ?? "");
      if (dateCompare !== 0) return dateCompare;
      if (a.finishRatio === null && b.finishRatio !== null) return 1;
      if (b.finishRatio === null && a.finishRatio !== null) return -1;
      if (a.finishRatio !== null && b.finishRatio !== null && a.finishRatio !== b.finishRatio) {
        return a.finishRatio - b.finishRatio;
      }
      if ((b.playerCount ?? 0) !== (a.playerCount ?? 0)) {
        return (b.playerCount ?? 0) - (a.playerCount ?? 0);
      }
      return a.tournamentName.localeCompare(b.tournamentName);
    });
}

async function fetchPlayerAchievements(playerId: string, topdeckId: string): Promise<PlayerAchievementRow[]> {
  const rows = await fetchPlayerTournamentEntries(playerId);
  return buildPlayerAchievements(rows, topdeckId);
}

function buildPlayerCommanderUsageRows(
  rows: PlayerTournamentEntryRow[],
  topdeckId: string,
  playerName: string
): PlayerCommanderUsageRow[] {
  return rows
    .map((row) => {
      const tournament = firstRelation(row.tournaments);
      const commander = firstRelation(row.commanders);
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
        tournament_name: tournament?.name ?? null,
        tournament_topdeck_tid: tournament?.topdeck_tid ?? null,
      };
    })
    .filter((row) => row.commander_name && row.start_date);
}

async function fetchPlayerCommanderUsageRows(
  playerId: string,
  topdeckId: string,
  playerName: string
): Promise<PlayerCommanderUsageRow[]> {
  const rows = await fetchPlayerTournamentEntries(playerId);
  return buildPlayerCommanderUsageRows(rows, topdeckId, playerName);
}

async function fetchActiveCommander(
  playerId: string,
  topdeckId: string,
  playerName: string,
  usageRows?: PlayerCommanderUsageRow[]
): Promise<string | null> {
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
  const commanderUsageRows = usageRows ?? (await fetchPlayerCommanderUsageRows(playerId, topdeckId, playerName));
  const forecastRows = selectCommanderForecastRows([topdeckId], commanderUsageRows, referenceDate);
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
        commanderName,
        opponents: pod,
      } satisfies PlayerGameLog;
    })
    .filter((value): value is PlayerGameLog => Boolean(value))
    .sort((a, b) => b.startDate.localeCompare(a.startDate));
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
  const eventLogTables = ["global_elo_game_event_log", "regional_elo_game_event_log"];
  let eventRows: PlayerEventLogRow[] = [];
  let eventLogTable = eventLogTables[0];
  let lastEventError: unknown = null;

  for (const table of eventLogTables) {
    const collected: PlayerEventLogRow[] = [];
    let queryFailed = false;
    let queryError: unknown = null;

    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      let query = supabase
        .from(table)
        .select(
          "game_id, game_date, tournament_name, state, round_number, round_name, table_number, seat_position, commander_name, game_result"
        )
        .eq("player_id", playerId)
        .order("game_date", { ascending: false })
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (regionFilter) {
        query = query.ilike("state", regionFilter);
      }

      const { data, error } = await query;
      if (error) {
        queryFailed = true;
        queryError = error;
        break;
      }

      collected.push(...((data as PlayerEventLogRow[]) ?? []));
      if (!data || data.length < SUPABASE_PAGE_SIZE) break;
    }

    if (!queryFailed) {
      eventRows = collected;
      eventLogTable = table;
      break;
    }
    lastEventError = queryError;
  }

  if (lastEventError && eventRows.length === 0 && eventLogTable === eventLogTables[0]) {
    console.error("Error fetching precomputed player event log:", describeSupabaseError(lastEventError));
    return [];
  }
  if (eventRows.length === 0) return [];

  const gameIds = Array.from(new Set(eventRows.map((row) => row.game_id)));
  const opponentRows: PlayerEventOpponentRow[] = [];
  for (const gameIdChunk of chunkArray(gameIds, 250)) {
    for (let offset = 0; ; offset += SUPABASE_PAGE_SIZE) {
      const { data: opponentData, error: opponentError } = await supabase
        .from(eventLogTable)
        .select("game_id, player_id, player_name, topdeck_id, seat_position, commander_name, game_result")
        .in("game_id", gameIdChunk)
        .neq("player_id", playerId)
        .range(offset, offset + SUPABASE_PAGE_SIZE - 1);

      if (opponentError) {
        console.error(
          "Error fetching precomputed player event opponents:",
          describeSupabaseError(opponentError)
        );
        break;
      }
      opponentRows.push(...((opponentData as PlayerEventOpponentRow[]) ?? []));
      if (!opponentData || opponentData.length < SUPABASE_PAGE_SIZE) break;
    }
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

const fetchCachedGlobalEloRank = unstable_cache(
  async (playerId: string) => fetchGlobalEloRank(playerId),
  ["regional-player-global-rank-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedRegionalRank = unstable_cache(
  async (playerId: string, regionKey: string) => fetchRegionalRank(playerId, regionKey),
  ["regional-player-local-rank-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedCountryRank = unstable_cache(
  async (playerId: string, countryKey: string) => fetchCountryRank(playerId, countryKey),
  ["regional-player-country-rank-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedRegionalRanks = unstable_cache(
  async (playerId: string) => fetchRegionalRanks(playerId),
  ["regional-player-regional-ranks-v2"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedPlayerProfileSummary = unstable_cache(
  async (playerId: string) => fetchPlayerProfileSummary(playerId),
  ["regional-player-profile-summary-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedPlayerAchievements = unstable_cache(
  async (playerId: string, topdeckId: string) => fetchPlayerAchievements(playerId, topdeckId),
  ["regional-player-achievements-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedPlayerCommanderUsageRows = unstable_cache(
  async (playerId: string, topdeckId: string, playerName: string) =>
    fetchPlayerCommanderUsageRows(playerId, topdeckId, playerName),
  ["regional-player-commander-usage-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

const fetchCachedPlayerEventLogs = unstable_cache(
  async (playerId: string, regionFilter: string) => fetchPlayerEventLogs(playerId, regionFilter),
  ["regional-player-event-logs-v3"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

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
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const topdeckId = resolvedParams.topdeckId;
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim().toUpperCase();
  const regionFilter = requestedRegion === "ALL" ? "" : requestedRegion;
  const requestedAchievementsPage = readPositiveIntParam(resolvedSearchParams, "achievementsPage");
  const achievementTournamentSearch = readStringParam(resolvedSearchParams, "achievementTournament");
  const achievementCommanderSearch = readStringParam(resolvedSearchParams, "achievementCommander");

  const player = await fetchPlayer(topdeckId);
  if (!player) {
    return (
      <main className="container mx-auto px-4 py-10">
        <p className="text-sm text-muted-foreground">No player found for TopDeck ID {topdeckId}.</p>
      </main>
    );
  }

  const [
    globalSnapshot,
    globalEloRank,
    regionalRanks,
    profileSummary,
    commanderUsageRows,
    fetchedAchievementRows,
  ] = await Promise.all([
    fetchGlobalSnapshot(topdeckId),
    fetchCachedGlobalEloRank(player.id),
    fetchCachedRegionalRanks(player.id),
    fetchCachedPlayerProfileSummary(player.id),
    fetchCachedPlayerCommanderUsageRows(player.id, topdeckId, player.name),
    fetchCachedPlayerAchievements(player.id, topdeckId),
  ]);
  const activeCommander = await fetchActiveCommander(player.id, topdeckId, player.name, commanderUsageRows);
  const regionalRankRows = regionalRanks.map((row) => ({
    ...row,
    country_key: row.country_key ?? inferCountryForRegion(row.region_key) ?? "UNKNOWN",
  }));
  const eventPlayerLogsResult = await Promise.resolve(fetchCachedPlayerEventLogs(player.id, ""))
    .then((value) => ({ status: "fulfilled" as const, value }))
    .catch((reason) => ({ status: "rejected" as const, reason }));
  const eventPlayerLogs = eventPlayerLogsResult.status === "fulfilled" ? eventPlayerLogsResult.value : [];
  const playerLogs =
    eventPlayerLogs.length > 0
      ? eventPlayerLogs
      : await fetchEntries(player.id).then((entries) => buildPlayerLogsFromRawHistory(entries));
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
    .map((row) => {
      const gameResults = achievementResultByTournament.get(
        achievementTournamentKey(row.tournamentName, row.startDate)
      );
      if (!gameResults?.games) return row;
      return {
        ...row,
        wins: gameResults.wins,
        draws: gameResults.draws,
        losses: gameResults.losses,
        recordGames: gameResults.games,
      };
    })
    .filter((row) => row.recordGames > 0);
  const normalizedAchievementTournamentSearch = achievementTournamentSearch.toLocaleLowerCase();
  const normalizedAchievementCommanderSearch = achievementCommanderSearch.toLocaleLowerCase();
  const achievementRows = allAchievementRows.filter((row) => {
    const matchesTournament =
      !normalizedAchievementTournamentSearch ||
      row.tournamentName.toLocaleLowerCase().includes(normalizedAchievementTournamentSearch);
    const matchesCommander =
      !normalizedAchievementCommanderSearch ||
      (row.commanderName ?? "Unknown").toLocaleLowerCase().includes(normalizedAchievementCommanderSearch);
    return matchesTournament && matchesCommander;
  });
  const achievementPageCount = Math.max(1, Math.ceil(achievementRows.length / ACHIEVEMENTS_PAGE_SIZE));
  const achievementPage = Math.min(requestedAchievementsPage, achievementPageCount);
  const visibleAchievementRows = achievementRows.slice(
    (achievementPage - 1) * ACHIEVEMENTS_PAGE_SIZE,
    achievementPage * ACHIEVEMENTS_PAGE_SIZE
  );

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
  const canonicalGames = totalGames;
  const canonicalWins = totalWins;
  const canonicalDraws = totalDraws;
  const canonicalLosses = totalLosses;
  const assignmentRowsByRegion = new Map<string, StateAssignmentRow>();
  const historicalRegionKeys = new Set<string>();
  if (profileSummary?.state_assignments?.length) {
    for (const row of profileSummary.state_assignments) {
      assignmentRowsByRegion.set(row.region_key, row);
    }
  } else {
    for (const row of regionalRankRows) {
      const regionKey = row.region_key ?? "";
      if (!regionKey) continue;
      assignmentRowsByRegion.set(regionKey, {
        country_key: row.country_key ?? inferCountryForRegion(regionKey) ?? "UNKNOWN",
        region_key: regionKey,
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
  }
  const derivedHomeRegion =
    Array.from(assignmentRowsByRegion.values())
      .filter((row) => row.region_key !== "UNKNOWN")
      .sort((a, b) => {
        if (b.games_played !== a.games_played) return b.games_played - a.games_played;
        return a.region_key.localeCompare(b.region_key);
      })[0]?.region_key ?? null;
  const homeRegion = globalEloRank?.primary_region_key ?? profileSummary?.home_region_key ?? regionalRanks[0]?.region_key ?? derivedHomeRegion;
  const homeCountry =
    profileSummary?.home_country_key ??
    globalEloRank?.primary_country_key ??
    (homeRegion ? inferCountryForRegion(homeRegion) : null) ??
    (regionalRankRows[0]?.country_key ?? null);
  const selectedRegion = regionFilter || homeRegion || "";
  const regionalRank = await fetchCachedRegionalRank(player.id, selectedRegion);
  const countryRank = await fetchCachedCountryRank(player.id, homeCountry ?? "");
  const activeRank = regionalRank;
  const displayedTopdeckElo =
    globalEloRank?.topdeck_elo ?? activeRank?.topdeck_elo ?? countryRank?.topdeck_elo ?? null;
  const shouldShowGlobalRank = isActiveRank(globalEloRank);
  const shouldShowLocalRank = isActiveRank(activeRank);
  const shouldShowCountryRank = isActiveRank(countryRank);
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
  const topdeckProfileHref = buildTopdeckProfileHref(topdeckId);
  const backHref = regionFilter
    ? `/regional-elo?scope=state&region=${encodeURIComponent(regionFilter)}`
    : "/regional-elo";
  const stateLeaderboardHref = homeRegion
    ? `/regional-elo?scope=country&country=${encodeURIComponent(
        inferCountryForRegion(homeRegion) ?? "UNITED STATES"
      )}&region=${encodeURIComponent(homeRegion)}`
    : null;
  const countryLeaderboardHref = homeCountry
    ? `/regional-elo?scope=country&country=${encodeURIComponent(homeCountry)}`
    : null;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <div className="space-y-3">
            <Link href={backHref} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to region leaderboard
            </Link>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  {player.name}
                </h1>
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

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-9">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  State Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {stateLeaderboardHref && shouldShowLocalRank && activeRank ? (
                    <Link href={stateLeaderboardHref} className="hover:text-primary">
                      #{activeRank.rank}
                    </Link>
                  ) : (
                    "--"
                  )}
                </div>
                <div className="text-sm text-muted-foreground">
                  {stateLeaderboardHref ? (
                    <Link href={stateLeaderboardHref} className="hover:text-primary">
                      {homeRegion}
                    </Link>
                  ) : (
                    "Unassigned"
                  )}
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Country Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {countryLeaderboardHref && shouldShowCountryRank && countryRank ? (
                    <Link href={countryLeaderboardHref} className="hover:text-primary">
                      #{countryRank.rank}
                    </Link>
                  ) : (
                    "--"
                  )}
                </div>
                <div className="text-sm text-muted-foreground">
                  {countryLeaderboardHref && homeCountry ? (
                    <Link href={countryLeaderboardHref} className="hover:text-primary">
                      {homeCountry}
                    </Link>
                  ) : (
                    "Unassigned"
                  )}
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Global Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {shouldShowGlobalRank && globalEloRank ? (
                    <Link href="/regional-elo" className="hover:text-primary">
                      #{globalEloRank.rank}
                    </Link>
                  ) : (
                    "--"
                  )}
                </div>
                <div className="text-sm text-muted-foreground">EARTH</div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  TopDeck Rank
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {topdeckProfileHref ? (
                  <a
                    href={topdeckProfileHref}
                    target="_blank"
                    rel="noreferrer"
                    className="block hover:text-primary"
                  >
                    <div className="text-2xl font-semibold text-foreground">
                      {globalSnapshot?.rank ? `#${globalSnapshot.rank}` : (globalEloRank?.topdeck_elo_rank ? `#${globalEloRank.topdeck_elo_rank}` : "—")}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {globalSnapshot?.points ? `${globalSnapshot.points} points` : (globalSnapshot ? "No points snapshot" : "Regional Rank")}
                    </div>
                  </a>
                ) : (
                  <>
                    <div className="text-2xl font-semibold text-foreground">
                      {globalSnapshot?.rank ? `#${globalSnapshot.rank}` : (globalEloRank?.topdeck_elo_rank ? `#${globalEloRank.topdeck_elo_rank}` : "—")}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {globalSnapshot?.points ? `${globalSnapshot.points} points` : (globalSnapshot ? "No points snapshot" : "Regional Rank")}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  TopDeck Elo
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {displayedTopdeckElo === null ? "—" : Math.round(displayedTopdeckElo)}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Hidden Elo
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
                  Unique Opponents
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {opponentRecords.length}
              </CardContent>
            </Card>
          </div>

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
                      <th className="px-2 py-3 text-right">W-L-D</th>
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
                                  {formatShortDate(latestTournament.date)} | {latestTournament.name}
                                </a>
                              ) : (
                                <span>
                                  {formatShortDate(latestTournament.date)} | {latestTournament.name}
                                </span>
                              )
                            ) : (
                              "—"
                            )}
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
                        <th className="px-2 py-3 text-right">W-L-D</th>
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
                              href={`/regional-elo/player/${topdeckId}?region=${encodeURIComponent(regionKey)}`}
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
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
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
              <form method="get" className="mb-4 grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
                {regionFilter ? <input type="hidden" name="region" value={regionFilter} /> : null}
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
                <button
                  type="submit"
                  className="self-end rounded-md border border-border/70 px-3 py-2 text-sm text-foreground hover:border-primary/40 hover:text-primary"
                >
                  Search
                </button>
                {achievementTournamentSearch || achievementCommanderSearch ? (
                  <Link
                    href={buildPlayerProfileHref(topdeckId, regionFilter, 1)}
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
                      <th className="px-2 py-3">Date</th>
                      <th className="px-2 py-3">Commander</th>
                      <th className="px-2 py-3 text-right">Finish</th>
                      <th className="px-2 py-3 text-right">W-L-D</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleAchievementRows.map((row, index) => (
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
                              className="text-foreground hover:text-primary"
                            >
                              {row.tournamentName}
                            </a>
                          ) : (
                            <span className="text-foreground">{row.tournamentName}</span>
                          )}
                        </td>
                        <td className="px-2 py-3 text-muted-foreground">
                          {formatShortDate(row.startDate)}
                        </td>
                        <td className="px-2 py-3 text-muted-foreground">
                          {row.commanderName && row.decklistUrl ? (
                            <a
                              href={row.decklistUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-foreground hover:text-primary"
                            >
                              {row.commanderName}
                            </a>
                          ) : (
                            row.commanderName ?? "Unknown"
                          )}
                        </td>
                        <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                          {formatPlacementRatio(row.placement, row.playerCount)}
                        </td>
                        <td className="px-2 py-3 text-right font-mono text-muted-foreground">
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
                          achievementCommanderSearch
                        )}
                        className="rounded-md border border-border/70 px-3 py-1.5 text-foreground hover:border-primary/40 hover:text-primary"
                      >
                        Previous
                      </Link>
                    ) : (
                      <span className="rounded-md border border-border/40 px-3 py-1.5 text-muted-foreground/60">
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
                          achievementCommanderSearch
                        )}
                        className="rounded-md border border-border/70 px-3 py-1.5 text-foreground hover:border-primary/40 hover:text-primary"
                      >
                        Next
                      </Link>
                    ) : (
                      <span className="rounded-md border border-border/40 px-3 py-1.5 text-muted-foreground/60">
                        Next
                      </span>
                    )}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
