import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { RegionalLeaderboardTable } from "./regional-leaderboard-table";
import { RegionSelector } from "./region-selector";
import { unstable_cache } from "next/cache";

export const dynamic = "force-dynamic";
const GLOBAL_REGION_KEY = "ALL";
const LEADERBOARD_PAGE_SIZE = 50;
const REGIONAL_ELO_CACHE_REVALIDATE_SECONDS = 60 * 15; // 15 minutes

function readRegionParam(
  params: Awaited<Promise<{ region?: string | string[] }> | { region?: string | string[] }> | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return "";
  if (typeof (anyParams as URLSearchParams).get === "function") {
    return (anyParams as URLSearchParams).get("region") ?? "";
  }
  const value = (anyParams as Record<string, string | string[] | undefined>).region;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readCountryParam(
  params:
    | Awaited<Promise<{ country?: string | string[] }> | { country?: string | string[] }>
    | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return "";
  if (typeof (anyParams as URLSearchParams).get === "function") {
    return (anyParams as URLSearchParams).get("country") ?? "";
  }
  const value = (anyParams as Record<string, string | string[] | undefined>).country;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readScopeParam(
  params:
    | Awaited<Promise<{ scope?: string | string[] }> | { scope?: string | string[] }>
    | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return "";
  if (typeof (anyParams as URLSearchParams).get === "function") {
    return (anyParams as URLSearchParams).get("scope") ?? "";
  }
  const value = (anyParams as Record<string, string | string[] | undefined>).scope;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readSearchParam(
  params: Awaited<Promise<{ q?: string | string[] }> | { q?: string | string[] }> | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return "";
  if (typeof (anyParams as URLSearchParams).get === "function") {
    return (anyParams as URLSearchParams).get("q") ?? "";
  }
  const value = (anyParams as Record<string, string | string[] | undefined>).q;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function readPageParam(
  params:
    | Awaited<Promise<Record<string, string | string[] | undefined>> | Record<string, string | string[] | undefined>>
    | URLSearchParams
    | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return 1;
  const pageValue =
    typeof (anyParams as URLSearchParams).get === "function"
      ? (anyParams as URLSearchParams).get("page")
      : (anyParams as Record<string, string | string[] | undefined>).page;
  const rawValue = Array.isArray(pageValue) ? pageValue[0] ?? "" : pageValue ?? "";
  const parsed = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

type RegionRow = {
  region_type: string;
  region_key: string;
  country_key: string | null;
  player_count: number;
  updated_at: string | null;
};

type LeaderboardRow = {
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
  hidden_rating?: number;
  topdeck_elo?: number | null;
  topdeck_elo_rank?: number | null;
};

type LatestCommanderRow = {
  topdeck_id: string | null;
  active_commander: string | null;
  active_commander_decklist_url: string | null;
  latest_tournament_name: string | null;
  latest_tournament_date: string | null;
  latest_tournament_topdeck_tid: string | null;
};

function isKnownCommander(commanderName: string | null | undefined) {
  const normalized = (commanderName ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

type LeaderboardPage = {
  rows: LeaderboardRow[];
  totalCount: number;
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function logReadSummary(event: string, details: Record<string, unknown>) {
  console.info(`[regional-elo] ${event}`, details);
}

function normalizeLeaderboardRows(rows: LeaderboardRow[]): LeaderboardRow[] {
  return rows.map((row) => ({
    ...row,
    hidden_rating: row.rating,
    topdeck_elo: row.topdeck_elo ?? null,
    topdeck_elo_rank: row.topdeck_elo_rank ?? null,
  }));
}

async function fetchLeaderboardRows(
  regionType: "global" | "country" | "state",
  regionKey: string,
  page: number,
  pageSize: number,
  searchQuery = ""
): Promise<LeaderboardPage> {
  const pageStart = (page - 1) * pageSize;
  const normalizedSearch = searchQuery.trim();
  let query = supabase
    .from("global_elo_active_leaderboard")
    .select(
      "region_type, region_key, country_key, primary_country_key, primary_region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank, topdeck_elo, topdeck_elo_rank",
      { count: "exact" }
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .order("topdeck_elo_rank", { ascending: true, nullsFirst: false })
    .order("player_name", { ascending: true })
    .range(pageStart, pageStart + pageSize - 1);

  if (normalizedSearch) {
    query = query.ilike("player_name", `%${normalizedSearch}%`);
  }

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
  return {
    rows,
    totalCount: count ?? 0,
  };
}

async function fetchRegionRows(): Promise<RegionRow[]> {
  const { data, error } = await supabase
    .from("global_elo_regions")
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
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}

async function fetchLatestCommanders(
  rows: Array<{ player_id?: string; topdeck_id: string | null }>
): Promise<Map<string, LatestCommanderRow>> {
  const topdeckIds = rows
    .map((row) => row.topdeck_id)
    .filter((value): value is string => Boolean(value));
  if (topdeckIds.length === 0) return new Map();

  const latestByPlayer = new Map<string, LatestCommanderRow>();
  for (const row of rows) {
    if (!row.topdeck_id) continue;
    latestByPlayer.set(row.topdeck_id, {
      topdeck_id: row.topdeck_id,
      active_commander: null,
      active_commander_decklist_url: null,
      latest_tournament_name: null,
      latest_tournament_date: null,
      latest_tournament_topdeck_tid: null,
    });
  }

  // Layer 1: Try enriched profile query (includes tournament metadata)
  const profileRows: Array<{
    topdeck_id: string | null;
    active_commander: string | null;
    latest_decklist_url: string | null;
    latest_tournament_name?: string | null;
    latest_tournament_date?: string | null;
    latest_tournament_topdeck_tid?: string | null;
  }> = [];

  for (const topdeckIdChunk of chunkArray(topdeckIds, 250)) {
    const { data, error } = await supabase
      .from("player_commander_profiles")
      .select("topdeck_id, active_commander, latest_decklist_url, latest_tournament_name, latest_tournament_date, latest_tournament_topdeck_tid")
      .in("topdeck_id", topdeckIdChunk);

    if (error) {
      // Layer 2: Safe profile query (only basic columns known to exist in older schemas)
      console.warn("[regional-elo] Enriched profile query failed, trying safe query:", error.message);
      const { data: safeData, error: safeError } = await supabase
        .from("player_commander_profiles")
        .select("topdeck_id, active_commander, latest_decklist_url")
        .in("topdeck_id", topdeckIdChunk);

      if (safeError) {
        console.error("[regional-elo] Safe profile query also failed:", safeError.message);
        continue;
      }
      if (safeData) {
        profileRows.push(...(safeData as Array<{
          topdeck_id: string | null;
          active_commander: string | null;
          latest_decklist_url: string | null;
        }>));
      }
    } else if (data) {
      profileRows.push(...(data as Array<{
        topdeck_id: string | null;
        active_commander: string | null;
        latest_decklist_url: string | null;
        latest_tournament_name?: string | null;
        latest_tournament_date?: string | null;
        latest_tournament_topdeck_tid?: string | null;
      }>));
    }
  }

  for (const row of profileRows) {
    if (!row.topdeck_id) continue;
    const existing = latestByPlayer.get(row.topdeck_id);
    if (!existing) continue;
    existing.active_commander = isKnownCommander(row.active_commander) ? row.active_commander : null;
    existing.active_commander_decklist_url = row.latest_decklist_url ?? null;
    existing.latest_tournament_name = row.latest_tournament_name ?? null;
    existing.latest_tournament_date = row.latest_tournament_date ?? null;
    existing.latest_tournament_topdeck_tid = row.latest_tournament_topdeck_tid ?? null;
  }

  // Layer 3: Fallback to event logs for missing tournament OR missing commander data
  const playersNeedingFallback = Array.from(latestByPlayer.values())
    .filter((row) => !row.latest_tournament_name || !row.active_commander)
    .map((row) => rows.find((r) => r.topdeck_id === row.topdeck_id)?.player_id)
    .filter((id): id is string => Boolean(id));

  if (playersNeedingFallback.length > 0) {
    const fallbackData = new Map<string, { commander: string | null; tournament: string | null; date: string | null; tournament_id: string | null }>();
    
    for (const table of ["global_elo_game_event_log", "regional_elo_game_event_log"]) {
      const { data, error } = await supabase
        .from(table)
        .select("player_id, game_date, tournament_name, tournament_id, commander_name")
        .in("player_id", playersNeedingFallback)
        .order("game_date", { ascending: false })
        .limit(500);

      if (error) continue;

      for (const row of (data ?? []) as Array<{ player_id: string; game_date: string | null; tournament_name: string | null; tournament_id: string | null; commander_name: string | null }>) {
        if (fallbackData.has(row.player_id)) continue;
        fallbackData.set(row.player_id, {
          commander: row.commander_name ?? null,
          tournament: row.tournament_name ?? null,
          date: row.game_date ?? null,
          tournament_id: row.tournament_id ?? null,
        });
      }
      if (fallbackData.size === playersNeedingFallback.length) break;
    }

    const tournamentIds = Array.from(new Set(Array.from(fallbackData.values()).map((row) => row.tournament_id).filter((id): id is string => Boolean(id))));
    const tournamentMetadataById = new Map<string, { name: string | null; date: string | null; topdeck_tid: string | null }>();
    
    if (tournamentIds.length > 0) {
      const { data, error } = await supabase
        .from("tournaments")
        .select("id, name, start_date, topdeck_tid")
        .in("id", tournamentIds);

      if (!error && data) {
        for (const t of (data as Array<{ id: string; name: string | null; start_date: string | null; topdeck_tid: string | null }>)) {
          tournamentMetadataById.set(t.id, {
            name: t.name ?? null,
            date: t.start_date ?? null,
            topdeck_tid: t.topdeck_tid ?? null
          });
        }
      }
    }

    for (const row of rows) {
      if (!row.topdeck_id || !row.player_id) continue;
      const fallback = fallbackData.get(row.player_id);
      if (!fallback) continue;
      const existing = latestByPlayer.get(row.topdeck_id);
      if (!existing) continue;

      if (!existing.active_commander) {
        existing.active_commander = isKnownCommander(fallback.commander) ? fallback.commander : null;
      }
      
      if (!existing.latest_tournament_name) {
        const meta = fallback.tournament_id ? tournamentMetadataById.get(fallback.tournament_id) : null;
        existing.latest_tournament_name = meta?.name ?? fallback.tournament;
        existing.latest_tournament_date = meta?.date ?? fallback.date;
        existing.latest_tournament_topdeck_tid = meta?.topdeck_tid ?? null;
      }
    }
  }

  logReadSummary("latest-commanders-cache-miss", {
    players: rows.length,
    profilesFound: profileRows.length,
    fallbacksUsed: playersNeedingFallback.length,
  });

  return latestByPlayer;
}

const getCachedRegionRows = unstable_cache(
  fetchRegionRows,
  ["regional-elo-regions-v2"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS }
);

const getCachedLeaderboardRows = unstable_cache(
  async (
    regionType: "global" | "country" | "state",
    regionKey: string,
    page: number,
    pageSize: number,
    searchQuery: string
  ) => fetchLeaderboardRows(regionType, regionKey, page, pageSize, searchQuery),
  ["regional-elo-leaderboard-v4"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS }
);

const getCachedLatestCommanders = unstable_cache(
  async (players: Array<{ player_id: string; topdeck_id: string }>) => {
    // We fetch profiles using IDs to ensure the cache key is stable and specific to the players shown.
    const map = await fetchLatestCommanders(players);
    return Object.fromEntries(map.entries());
  },
  ["regional-elo-latest-commanders-v4"],
  { revalidate: REGIONAL_ELO_CACHE_REVALIDATE_SECONDS }
);

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?:
    | { country?: string | string[]; q?: string | string[]; region?: string | string[]; scope?: string | string[] }
    | Promise<{ country?: string | string[]; q?: string | string[]; region?: string | string[]; scope?: string | string[] }>;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const regions = await getCachedRegionRows();
  const requestedScope = readScopeParam(resolvedSearchParams).trim().toLowerCase();
  const requestedCountry = decodeURIComponent(readCountryParam(resolvedSearchParams)).trim();
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim();
  const playerSearch = decodeURIComponent(readSearchParam(resolvedSearchParams)).trim();
  const requestedPage = readPageParam(resolvedSearchParams);
  const countryRegions = regions.filter((region) => region.region_type === "country");
  const hasCountryOptions = countryRegions.length > 0;
  const selectedScope: "global" | "country" =
    hasCountryOptions && requestedScope === "country" ? "country" : "global";
  const defaultCountry =
    countryRegions.find((region) => region.region_key === "UNITED STATES")?.region_key ||
    countryRegions[0]?.region_key;
  const selectedCountry =
    countryRegions.find((region) => region.region_key === requestedCountry)?.region_key ||
    countryRegions.find((region) => region.region_key.toUpperCase() === requestedCountry.toUpperCase())
      ?.region_key ||
    defaultCountry;
  const stateRegionsForCountry = hasCountryOptions
    ? regions.filter((region) => region.region_type === "state" && region.country_key === selectedCountry)
    : regions.filter((region) => region.region_type === "state");
  const selectedRegion =
    stateRegionsForCountry.find((region) => region.region_key === requestedRegion)?.region_key ||
    stateRegionsForCountry.find(
      (region) =>
        region.region_key.toUpperCase() === requestedRegion.toUpperCase()
    )?.region_key;
  const activeRegionType =
    selectedScope === "global" ? "global" : selectedRegion ? "state" : "country";
  const activeRegionKey =
    selectedScope === "global" ? GLOBAL_REGION_KEY : selectedRegion || selectedCountry || "";

  const leaderboardPage =
    activeRegionKey
      ? await getCachedLeaderboardRows(
          activeRegionType,
          activeRegionKey,
          requestedPage,
          LEADERBOARD_PAGE_SIZE,
          playerSearch
        )
      : { rows: [], totalCount: 0 };

  const totalPages = Math.max(Math.ceil(leaderboardPage.totalCount / LEADERBOARD_PAGE_SIZE), 1);
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
              playerSearch
            )
          ).rows
        : [];
  const leaderboard = leaderboardRows;

  const playerKeys = leaderboard
    .map((r) => ({ player_id: r.player_id, topdeck_id: r.topdeck_id }))
    .filter((p): p is { player_id: string; topdeck_id: string } => Boolean(p.topdeck_id));

  const latestByPlayerRecord = await getCachedLatestCommanders(playerKeys);


  const updatedAt =
    regions.find((r) =>
      activeRegionType === "global"
        ? r.region_type === "global" && r.region_key === GLOBAL_REGION_KEY
        : r.region_type === activeRegionType && r.region_key === activeRegionKey
    )?.updated_at ?? null;
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <Link className="transition hover:text-foreground" href="/">
              Home
            </Link>
            <Link className="transition hover:text-foreground" href="/tournament-likelihood">
              Tournament Prep
            </Link>
            <Link className="transition hover:text-foreground" href="/about">
              Elo methodology
            </Link>
          </nav>
          <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[1fr_350px] xl:items-start xl:gap-12">
            <div className="flex flex-col gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  Global Leaderboard
                </h1>
              </div>
              <p className="text-base text-muted-foreground">
                TopDeck Elo is shown for players with a published TopDeck Elo snapshot. Country and
                state views are filtered slices of the local active player set.
              </p>
              <p className="text-sm text-muted-foreground">
                Rating model details:{" "}
                <Link href="/methodology/elo" className="text-primary hover:text-foreground">
                  cEDH Elo methodology
                </Link>
              </p>
            </div>
            <Card className="knd-panel w-full">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Region</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <RegionSelector
                  regions={regions}
                  selectedScope={selectedScope}
                  selectedCountry={selectedCountry}
                  selectedRegion={selectedRegion}
                  supportsCountryRegions={hasCountryOptions}
                />
                <div className="text-xs text-muted-foreground">
                  Updated {updatedAt ? formatDate(updatedAt) : "—"}
                </div>
              </CardContent>
            </Card>
          </div>
        </header>

        <div className="mt-8 space-y-6">

          <Card className="knd-panel">
            <CardHeader className="gap-4 md:flex-row md:items-end md:justify-between">
              <div className="space-y-2">
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Top Players
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Active view: {activeRegionType === "global" ? "Global" : activeRegionKey || "—"}
                </p>
              </div>
              <form action="/regional-elo" method="get" className="flex w-full flex-col gap-2 md:max-w-sm md:flex-row">
                <input type="hidden" name="scope" value={selectedScope} />
                {selectedScope === "country" && selectedCountry ? (
                  <input type="hidden" name="country" value={selectedCountry} />
                ) : null}
                {selectedScope === "country" && selectedRegion ? (
                  <input type="hidden" name="region" value={selectedRegion} />
                ) : null}
                <input type="hidden" name="page" value="1" />
                <label className="sr-only" htmlFor="leaderboard-player-search">
                  Player search
                </label>
                <input
                  id="leaderboard-player-search"
                  type="search"
                  name="q"
                  defaultValue={playerSearch}
                  className="knd-input"
                  placeholder="Search player name"
                />
                <button
                  type="submit"
                  className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-background"
                >
                  Search
                </button>
              </form>
            </CardHeader>
            <CardContent>
              <RegionalLeaderboardTable
                latestByPlayer={latestByPlayerRecord}
                leaderboard={leaderboard}
                currentPage={currentPage}
                totalCount={leaderboardPage.totalCount}
                pageSize={LEADERBOARD_PAGE_SIZE}
                selectedScope={selectedScope}
                selectedCountry={selectedCountry}
                selectedRegion={selectedRegion}
                playerSearch={playerSearch}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
