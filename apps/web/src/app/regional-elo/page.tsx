import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { RegionalLeaderboardTable } from "./regional-leaderboard-table";
import { RegionSelector } from "./region-selector";
import { inferCountryForRegion } from "@/lib/region-countries";

export const dynamic = "force-dynamic";
const GLOBAL_REGION_KEY = "ALL";
const LEADERBOARD_LIMIT = 50;
const INITIAL_COMMANDER_LOOKUP_LIMIT = 50;
const ACTIVE_PLAYER_LOOKBACK_MONTHS = 6;

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
};

type LatestCommanderRow = {
  topdeck_id: string | null;
  active_commander: string | null;
  latest_commander: string | null;
  latest_commander_date: string | null;
};

function isKnownCommander(commanderName: string | null | undefined) {
  const normalized = (commanderName ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function activePlayerCutoffDate() {
  const cutoff = new Date();
  cutoff.setMonth(cutoff.getMonth() - ACTIVE_PLAYER_LOOKBACK_MONTHS);
  return cutoff.toISOString().slice(0, 10);
}

async function fetchLeaderboardRows(
  regionType: "global" | "country" | "state",
  regionKey: string,
  maxRows = LEADERBOARD_LIMIT
): Promise<LeaderboardRow[]> {
  const pageSize = 1000;
  const rows: LeaderboardRow[] = [];
  const cutoffDate = activePlayerCutoffDate();

  for (let offset = 0; offset < maxRows; offset += pageSize) {
    const remaining = maxRows - offset;
    const pageEnd = offset + Math.min(pageSize, remaining) - 1;
    let query = supabase
      .from("global_elo_active_leaderboard")
      .select(
        "region_type, region_key, country_key, primary_country_key, primary_region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank"
      )
      .eq("region_type", regionType)
      .order("rank", { ascending: true })
      .range(offset, pageEnd);

    if (regionType === "global") {
      query = query.eq("region_key", GLOBAL_REGION_KEY);
    } else {
      query = query.eq("region_key", regionKey);
    }

    const { data, error } = await query;

    if (error) {
      return fetchLeaderboardRowsFromView(regionType, regionKey, maxRows, cutoffDate);
    }
    if (!data?.length) break;
    rows.push(...(data as LeaderboardRow[]));
    if (data.length < pageSize || rows.length >= maxRows) break;
  }

  return rows;
}

async function fetchLeaderboardRowsFromView(
  regionType: "global" | "country" | "state",
  regionKey: string,
  maxRows: number,
  cutoffDate: string
): Promise<LeaderboardRow[]> {
  const { data, error } = await supabase
    .from("global_elo_leaderboard")
    .select(
      "region_type, region_key, country_key, primary_country_key, primary_region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank"
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .gte("last_game_date", cutoffDate)
    .order("rating", { ascending: false })
    .order("games_played", { ascending: false })
    .range(0, maxRows - 1);

  if (error) {
    return fetchLegacyLeaderboardRows(
      regionType === "country" ? "global" : regionType,
      regionType === "country" ? GLOBAL_REGION_KEY : regionKey,
      maxRows
    );
  }

  return (data as LeaderboardRow[]) ?? [];
}

async function fetchLegacyLeaderboardRows(
  regionType: "global" | "state",
  regionKey: string,
  maxRows = LEADERBOARD_LIMIT
): Promise<LeaderboardRow[]> {
  const cutoffDate = activePlayerCutoffDate();
  const { data, error } = await supabase
    .from("regional_elo_leaderboard")
    .select(
      "region_type, region_key, primary_region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank"
    )
    .eq("region_type", regionType)
    .eq("region_key", regionKey)
    .gte("last_game_date", cutoffDate)
    .order("rank", { ascending: true })
    .range(0, maxRows - 1);

  if (error) {
    console.error("Error fetching legacy leaderboard rows:", error);
    return [];
  }

  return (data as LeaderboardRow[]) ?? [];
}

async function fetchRegionRows(): Promise<{ rows: RegionRow[]; supportsCountry: boolean }> {
  const { data, error } = await supabase
    .from("global_elo_regions")
    .select("region_type, region_key, country_key, player_count, updated_at")
    .order("region_type", { ascending: true })
    .order("region_key", { ascending: true });

  if (!error) {
    return { rows: (data ?? []) as RegionRow[], supportsCountry: true };
  }

  const { data: fallbackData, error: fallbackError } = await supabase
    .from("regional_elo_regions")
    .select("region_type, region_key, player_count, updated_at")
    .order("region_type", { ascending: true })
    .order("region_key", { ascending: true });

  if (fallbackError) {
    console.error("Error fetching region rows:", fallbackError);
    return { rows: [], supportsCountry: false };
  }

  const fallbackRows = ((fallbackData ?? []) as Omit<RegionRow, "country_key">[]).map((row) => ({
    ...row,
    country_key: row.region_type === "state" ? inferCountryForRegion(row.region_key) : null,
  }));
  const inferredCountries = new Map<string, RegionRow>();
  for (const row of fallbackRows) {
    if (row.region_type !== "state" || !row.country_key) continue;
    const existing = inferredCountries.get(row.country_key);
    inferredCountries.set(row.country_key, {
      region_type: "country",
      region_key: row.country_key,
      country_key: row.country_key,
      player_count: (existing?.player_count ?? 0) + Number(row.player_count ?? 0),
      updated_at:
        existing?.updated_at && row.updated_at
          ? existing.updated_at > row.updated_at
            ? existing.updated_at
            : row.updated_at
          : existing?.updated_at ?? row.updated_at ?? null,
    });
  }
  const legacyCountryRows: RegionRow[] =
    fallbackRows.some((row) => row.region_type === "country")
      ? []
      : Array.from(inferredCountries.values()).sort((a, b) =>
          a.region_key.localeCompare(b.region_key)
        );

  return {
    rows: [
      ...legacyCountryRows,
      ...fallbackRows.map((row) => ({
        ...row,
        country_key: row.country_key ?? null,
      })),
    ],
    supportsCountry: false,
  };
}

function chunkArray<T>(values: T[], chunkSize: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < values.length; index += chunkSize) {
    chunks.push(values.slice(index, index + chunkSize));
  }
  return chunks;
}

async function fetchLatestCommanders(topdeckIds: string[]): Promise<Map<string, LatestCommanderRow>> {
  if (topdeckIds.length === 0) return new Map();

  const pageSize = 1000;
  const rows: LatestCommanderRow[] = [];
  for (const topdeckIdChunk of chunkArray(topdeckIds, 250)) {
    for (let offset = 0; ; offset += pageSize) {
      const { data, error } = await supabase
        .from("player_commander_profiles")
        .select("topdeck_id, active_commander, latest_commander, latest_commander_date")
        .in("topdeck_id", topdeckIdChunk)
        .order("latest_commander_date", { ascending: false })
        .range(offset, offset + pageSize - 1);

      if (error || !data?.length) break;
      rows.push(...(data as LatestCommanderRow[]));
      if (data.length < pageSize) break;
    }
  }

  const latestByPlayer = new Map<string, LatestCommanderRow>();
  for (const row of rows) {
    if (!row.topdeck_id || latestByPlayer.has(row.topdeck_id)) continue;
    if (!isKnownCommander(row.active_commander) && !isKnownCommander(row.latest_commander)) continue;
    latestByPlayer.set(row.topdeck_id, row);
  }
  if (latestByPlayer.size > 0) return latestByPlayer;

  return fetchLatestCommandersFromHistory(topdeckIds);
}

async function fetchLatestCommandersFromHistory(topdeckIds: string[]): Promise<Map<string, LatestCommanderRow>> {
  const rows: Array<{ topdeck_id: string | null; commander_name: string | null; start_date: string | null }> = [];
  for (const topdeckIdChunk of chunkArray(topdeckIds, 250)) {
    const { data, error } = await supabase
      .from("player_commander_entries")
      .select("topdeck_id, commander_name, start_date")
      .in("topdeck_id", topdeckIdChunk)
      .order("start_date", { ascending: false })
      .range(0, 999);

    if (error) {
      console.error("Error fetching legacy commander history:", error);
      continue;
    }
    rows.push(...((data ?? []) as Array<{ topdeck_id: string | null; commander_name: string | null; start_date: string | null }>));
  }

  const latestByPlayer = new Map<string, LatestCommanderRow>();
  for (const row of rows) {
    if (!row.topdeck_id || latestByPlayer.has(row.topdeck_id)) continue;
    if (!isKnownCommander(row.commander_name)) continue;
    latestByPlayer.set(row.topdeck_id, {
      topdeck_id: row.topdeck_id,
      active_commander: row.commander_name,
      latest_commander: row.commander_name,
      latest_commander_date: row.start_date,
    });
  }
  return latestByPlayer;
}

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?:
    | { country?: string | string[]; region?: string | string[]; scope?: string | string[] }
    | Promise<{ country?: string | string[]; region?: string | string[]; scope?: string | string[] }>;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const regionResult = await fetchRegionRows();

  const regions = regionResult.rows;
  const supportsCountryRegions = regionResult.supportsCountry;
  const requestedScope = readScopeParam(resolvedSearchParams).trim().toLowerCase();
  const requestedCountry = decodeURIComponent(readCountryParam(resolvedSearchParams)).trim();
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim();
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

  const leaderboard =
    activeRegionKey
      ? supportsCountryRegions
        ? await fetchLeaderboardRows(activeRegionType, activeRegionKey)
        : await fetchLegacyLeaderboardRows(
            activeRegionType === "state" ? "state" : "global",
            activeRegionType === "state" ? activeRegionKey : GLOBAL_REGION_KEY
          )
      : [];

  const topdeckIds = leaderboard
    .slice(0, INITIAL_COMMANDER_LOOKUP_LIMIT)
    .map((row) => row.topdeck_id)
    .filter((value): value is string => Boolean(value));
  const latestByPlayer = await fetchLatestCommanders(topdeckIds);
  const latestByPlayerRecord = Object.fromEntries(latestByPlayer.entries());

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
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="knd-chip">Global Elo</p>
              <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
                Global Leaderboard
              </h1>
            </div>
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
          </div>
          <p className="max-w-4xl text-base text-muted-foreground">
            Elo is computed globally across all included games. Country and state views are
            filtered slices of that global rating set.
          </p>
          <p className="text-sm text-muted-foreground">
            Rating model details:{" "}
            <Link href="/methodology/elo" className="text-primary hover:text-foreground">
              cEDH Elo methodology
            </Link>
          </p>
        </header>

        <div className="mt-8 space-y-6">
          <div className="grid gap-6 xl:grid-cols-[300px]">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Region</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
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

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                Top Players
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Active view: {activeRegionType === "global" ? "Global" : activeRegionKey || "—"}
              </p>
            </CardHeader>
            <CardContent>
              <RegionalLeaderboardTable
                latestByPlayer={latestByPlayerRecord}
                leaderboard={leaderboard}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
