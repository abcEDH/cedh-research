import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";
import { withTiming } from "@/lib/performance";
import { overlayEloDisplayStats } from "@/lib/elo-display-stats";

export const GLOBAL_REGION_KEY = "ALL";
export const LEADERBOARD_PAGE_SIZE = 50;
export const REGIONAL_ELO_CACHE_REVALIDATE_SECONDS = 60 * 60 * 24;

export type RegionalEloSearchParams = {
  country?: string | string[];
  q?: string | string[];
  region?: string | string[];
  scope?: string | string[];
  eloOnly?: string | string[];
  page?: string | string[];
};

export type RegionRow = {
  region_type: string;
  region_key: string;
  country_key: string | null;
  player_count: number;
  updated_at: string | null;
};

export type LeaderboardRow = {
  region_type: string;
  region_key: string;
  country_key?: string | null;
  primary_country_key?: string | null;
  primary_region_key?: string | null;
  player_id: string;
  player_name: string;
  topdeck_id: string | null;
  rating: number;
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
  last_game_date: string | null;
  rank: number;
  topdeck_elo?: number | null;
  topdeck_elo_rank?: number | null;
};

export type ClientLeaderboardRow = Omit<LeaderboardRow, "rating">;
export type LatestCommanderRow = {
  topdeck_id: string | null;
  active_commander: string | null;
  active_commander_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
};

type LeaderboardPage = { rows: LeaderboardRow[]; totalCount: number };

function readParam(
  params: RegionalEloSearchParams | URLSearchParams | undefined,
  key: string,
) {
  if (!params) return "";
  if (typeof (params as URLSearchParams).get === "function") {
    return (params as URLSearchParams).get(key) ?? "";
  }
  const value = (params as RegionalEloSearchParams)[
    key as keyof RegionalEloSearchParams
  ];
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

function readPageParam(
  params: RegionalEloSearchParams | URLSearchParams | undefined,
) {
  const parsed = Number.parseInt(readParam(params, "page"), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

function logReadSummary(event: string, details: Record<string, unknown>) {
  console.info(`[regional-elo] ${event}`, details);
}

function normalizeLeaderboardRows(rows: LeaderboardRow[]): LeaderboardRow[] {
  return rows.map((row) => ({
    ...row,
    topdeck_elo: row.topdeck_elo ?? null,
    topdeck_elo_rank: row.topdeck_elo_rank ?? null,
  }));
}

export function toClientLeaderboardRow(
  row: LeaderboardRow,
): ClientLeaderboardRow {
  const clientRow = { ...row } as Omit<LeaderboardRow, "rating"> & {
    rating?: number;
    hidden_rating?: number;
  };
  delete clientRow.rating;
  delete clientRow.hidden_rating;
  return clientRow;
}

async function fetchLeaderboardRows(
  regionType: "global" | "country" | "state",
  regionKey: string,
  page: number,
  pageSize: number,
  searchQuery = "",
): Promise<LeaderboardPage> {
  const normalizedSearch = searchQuery.trim();
  let query = supabase
    .from("global_elo_active_leaderboard")
    .select(
      "region_type, region_key, country_key, primary_country_key, primary_region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank, topdeck_elo, topdeck_elo_rank",
      { count: "exact" },
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .order("topdeck_elo_rank", { ascending: true, nullsFirst: false })
    .order("player_name", { ascending: true })
    .range((page - 1) * pageSize, page * pageSize - 1);
  if (normalizedSearch)
    query = query.ilike("player_name", `%${normalizedSearch}%`);
  const { data, error, count } = await query;
  if (error) {
    console.error("Error fetching active leaderboard rows:", error);
    throw error;
  }
  const rows = normalizeLeaderboardRows((data as LeaderboardRow[]) ?? []);
  logReadSummary("leaderboard-cache-miss", {
    source: "global_elo_active_leaderboard",
    regionType,
    regionKey,
    page,
    pageSize,
    search: normalizedSearch || null,
    rowsReturned: rows.length,
    totalCount: count ?? 0,
    supabaseQueries: 1,
  });
  return { rows, totalCount: count ?? 0 };
}

async function fetchRegionRows(): Promise<RegionRow[]> {
  const { data, error } = await supabase
    .from("global_elo_active_regions")
    .select("region_type, region_key, country_key, player_count, updated_at")
    .order("region_type", { ascending: true })
    .order("region_key", { ascending: true });
  if (error) {
    console.error("Error fetching region rows:", error);
    throw error;
  }
  return (data ?? []) as RegionRow[];
}

function chunkArray<T>(values: T[], chunkSize: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize)
    chunks.push(values.slice(index, index + chunkSize));
  return chunks;
}

function isKnownCommander(value: string | null | undefined) {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

async function fetchLatestCommanders(
  rows: Array<{ player_id?: string; topdeck_id: string | null }>,
): Promise<Map<string, LatestCommanderRow>> {
  const topdeckIds = rows
    .map((row) => row.topdeck_id)
    .filter((value): value is string => Boolean(value));
  if (!topdeckIds.length) return new Map();
  const latestByPlayer = new Map<string, LatestCommanderRow>();
  for (const topdeckId of topdeckIds)
    latestByPlayer.set(topdeckId, {
      topdeck_id: topdeckId,
      active_commander: null,
      active_commander_decklist_url: null,
      latest_tournament_name: null,
      latest_tournament_date: null,
      latest_tournament_topdeck_tid: null,
    });
  const profileRows: Array<{
    topdeck_id: string | null;
    active_commander: string | null;
    latest_decklist_url: string | null;
    latest_tournament_name?: string | null;
    latest_tournament_date?: string | null;
    latest_tournament_topdeck_tid?: string | null;
  }> = [];
  for (const chunk of chunkArray(topdeckIds, 250)) {
    const { data, error } = await supabase
      .from("player_commander_profiles")
      .select(
        "topdeck_id, active_commander, latest_decklist_url, latest_tournament_name, latest_tournament_date, latest_tournament_topdeck_tid",
      )
      .in("topdeck_id", chunk);
    if (error) {
      console.error("[regional-elo] Profile query failed:", error.message);
      continue;
    }
    if (data) profileRows.push(...(data as typeof profileRows));
  }
  for (const row of profileRows) {
    if (!row.topdeck_id) continue;
    const existing = latestByPlayer.get(row.topdeck_id);
    if (!existing) continue;
    existing.active_commander = isKnownCommander(row.active_commander)
      ? row.active_commander
      : null;
    existing.active_commander_decklist_url = row.latest_decklist_url ?? null;
    existing.latest_tournament_name = row.latest_tournament_name ?? null;
    existing.latest_tournament_date = row.latest_tournament_date ?? null;
    existing.latest_tournament_topdeck_tid =
      row.latest_tournament_topdeck_tid ?? null;
  }
  logReadSummary("latest-commanders-cache-miss", {
    players: rows.length,
    profilesFound: profileRows.length,
  });
  return latestByPlayer;
}

const getCachedRegionRows = unstable_cache(
  () => withTiming("regional-elo:regions", fetchRegionRows),
  ["regional-elo-regions-v5"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS },
);
const getCachedLeaderboardRows = unstable_cache(
  async (
    regionType: "global" | "country" | "state",
    regionKey: string,
    page: number,
    pageSize: number,
    searchQuery: string,
  ) =>
    withTiming("regional-elo:leaderboard", () =>
      fetchLeaderboardRows(regionType, regionKey, page, pageSize, searchQuery),
    ),
  ["regional-elo-leaderboard-v6"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS },
);
const getCachedLatestCommanders = unstable_cache(
  async (players: Array<{ player_id: string; topdeck_id: string }>) =>
    withTiming("regional-elo:latest-commanders", async () =>
      Object.fromEntries((await fetchLatestCommanders(players)).entries()),
    ),
  ["regional-elo-latest-commanders-v4"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS },
);

export async function loadRegionalEloData(
  searchParams?: RegionalEloSearchParams | URLSearchParams,
) {
  const rawEloOnly = readParam(searchParams, "eloOnly");
  const eloOnly = rawEloOnly !== "false";
  const regions = await getCachedRegionRows();
  const requestedScope = readParam(searchParams, "scope").trim().toLowerCase();
  const requestedCountry = decodeURIComponent(
    readParam(searchParams, "country"),
  ).trim();
  const requestedRegion = decodeURIComponent(
    readParam(searchParams, "region"),
  ).trim();
  const playerSearch = decodeURIComponent(readParam(searchParams, "q")).trim();
  const requestedPage = readPageParam(searchParams);
  const countryRegions = regions.filter(
    (region) => region.region_type === "country",
  );
  const hasCountryOptions = countryRegions.length > 0;
  const selectedScope: "global" | "country" =
    hasCountryOptions && requestedScope === "country" ? "country" : "global";
  const defaultCountry =
    countryRegions.find((region) => region.region_key === "UNITED STATES")
      ?.region_key || countryRegions[0]?.region_key;
  const selectedCountry =
    countryRegions.find((region) => region.region_key === requestedCountry)
      ?.region_key ||
    countryRegions.find(
      (region) =>
        region.region_key.toUpperCase() === requestedCountry.toUpperCase(),
    )?.region_key ||
    defaultCountry;
  const stateRegionsForCountry = hasCountryOptions
    ? regions.filter(
        (region) =>
          region.region_type === "state" &&
          region.country_key === selectedCountry,
      )
    : regions.filter((region) => region.region_type === "state");
  const selectedRegion =
    stateRegionsForCountry.find(
      (region) => region.region_key === requestedRegion,
    )?.region_key ||
    stateRegionsForCountry.find(
      (region) =>
        region.region_key.toUpperCase() === requestedRegion.toUpperCase(),
    )?.region_key;
  const activeRegionType =
    selectedScope === "global"
      ? "global"
      : selectedRegion
        ? "state"
        : "country";
  const activeRegionKey =
    selectedScope === "global"
      ? GLOBAL_REGION_KEY
      : selectedRegion || selectedCountry || "";
  const leaderboardPage = activeRegionKey
    ? await getCachedLeaderboardRows(
        activeRegionType,
        activeRegionKey,
        requestedPage,
        LEADERBOARD_PAGE_SIZE,
        playerSearch,
      )
    : { rows: [], totalCount: 0 };
  const totalPages = Math.max(
    Math.ceil(leaderboardPage.totalCount / LEADERBOARD_PAGE_SIZE),
    1,
  );
  const currentPage = Math.min(requestedPage, totalPages);
  const leaderboardRows =
    currentPage === requestedPage
      ? leaderboardPage.rows
      : activeRegionKey
        ? (
            await getCachedLeaderboardRows(
              activeRegionType,
              activeRegionKey,
              currentPage,
              LEADERBOARD_PAGE_SIZE,
              playerSearch,
            )
          ).rows
        : [];
  const leaderboardWithDisplayStats = await overlayEloDisplayStats(
    leaderboardRows,
    eloOnly ? "ranking" : "all",
  );
  const leaderboard = leaderboardWithDisplayStats.map(toClientLeaderboardRow);
  const playerKeys = leaderboard
    .map((r) => ({ player_id: r.player_id, topdeck_id: r.topdeck_id }))
    .filter((p): p is { player_id: string; topdeck_id: string } =>
      Boolean(p.topdeck_id),
    );
  const latestByPlayer = await getCachedLatestCommanders(playerKeys);
  const updatedAt =
    regions.find((r) =>
      activeRegionType === "global"
        ? r.region_type === "global" && r.region_key === GLOBAL_REGION_KEY
        : r.region_type === activeRegionType &&
          r.region_key === activeRegionKey,
    )?.updated_at ?? null;
  return {
    regions,
    eloOnly,
    selectedScope,
    selectedCountry,
    selectedRegion,
    hasCountryOptions,
    activeRegionType,
    activeRegionKey,
    leaderboardPage,
    currentPage,
    leaderboard,
    latestByPlayer,
    playerSearch,
    updatedAt,
  };
}
