import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { RegionSelector } from "./region-selector";

export const dynamic = "force-dynamic";

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

type RegionRow = {
  region_type: string;
  region_key: string;
  player_count: number;
  updated_at: string | null;
};

type LeaderboardRow = {
  region_type: string;
  region_key: string;
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
  commander_name: string | null;
  start_date: string | null;
};

type RegionalValidityRow = {
  region_type: string;
  region_key: string | null;
  scope: "global" | "region";
  total_tournaments: number;
  tournaments_with_state: number;
  tournaments_missing_state: number;
  total_games: number;
  included_games: number;
  excluded_games_missing_state: number;
  excluded_games_with_byes: number;
  excluded_games_insufficient_players: number;
  included_players: number;
  earliest_game_date: string | null;
  latest_game_date: string | null;
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

async function fetchAllRegionalRows(regionKey: string): Promise<LeaderboardRow[]> {
  const pageSize = 1000;
  const rows: LeaderboardRow[] = [];

  for (let offset = 0; ; offset += pageSize) {
    const { data, error } = await supabase
      .from("regional_elo_leaderboard")
      .select(
        "region_type, region_key, player_id, player_name, topdeck_id, rating, games_played, wins, draws, losses, last_game_date, rank"
      )
      .eq("region_type", "state")
      .eq("region_key", regionKey)
      .order("rating", { ascending: false })
      .range(offset, offset + pageSize - 1);

    if (error || !data?.length) break;
    rows.push(...(data as LeaderboardRow[]));
    if (data.length < pageSize) break;
  }

  return rows;
}

async function fetchLatestCommanders(topdeckIds: string[]): Promise<Map<string, LatestCommanderRow>> {
  if (topdeckIds.length === 0) return new Map();

  const pageSize = 1000;
  const rows: LatestCommanderRow[] = [];
  for (let offset = 0; ; offset += pageSize) {
    const { data, error } = await supabase
      .from("player_commander_entries")
      .select("topdeck_id, commander_name, start_date")
      .in("topdeck_id", topdeckIds)
      .order("start_date", { ascending: false })
      .range(offset, offset + pageSize - 1);

    if (error || !data?.length) break;
    rows.push(...(data as LatestCommanderRow[]));
    if (data.length < pageSize) break;
  }

  const latestByPlayer = new Map<string, LatestCommanderRow>();
  for (const row of rows) {
    if (!row.topdeck_id || latestByPlayer.has(row.topdeck_id)) continue;
    if (!isKnownCommander(row.commander_name)) continue;
    latestByPlayer.set(row.topdeck_id, row);
  }
  return latestByPlayer;
}

async function fetchRegionalValidity(): Promise<RegionalValidityRow[]> {
  const { data, error } = await supabase
    .from("regional_elo_data_validity")
    .select(
      [
        "region_type",
        "region_key",
        "scope",
        "total_tournaments",
        "tournaments_with_state",
        "tournaments_missing_state",
        "total_games",
        "included_games",
        "excluded_games_missing_state",
        "excluded_games_with_byes",
        "excluded_games_insufficient_players",
        "included_players",
        "earliest_game_date",
        "latest_game_date",
      ].join(", ")
    )
    .eq("region_type", "state");

  if (error) {
    console.error("Error fetching regional validity stats:", error);
    return [];
  }

  const rows = ((data ?? []) as unknown as Record<string, unknown>[]);

  return rows.map((row) => ({
    region_type: String(row.region_type ?? ""),
    region_key: row.region_key ? String(row.region_key) : null,
    scope: row.scope === "global" ? "global" : "region",
    total_tournaments: Number(row.total_tournaments ?? 0),
    tournaments_with_state: Number(row.tournaments_with_state ?? 0),
    tournaments_missing_state: Number(row.tournaments_missing_state ?? 0),
    total_games: Number(row.total_games ?? 0),
    included_games: Number(row.included_games ?? 0),
    excluded_games_missing_state: Number(row.excluded_games_missing_state ?? 0),
    excluded_games_with_byes: Number(row.excluded_games_with_byes ?? 0),
    excluded_games_insufficient_players: Number(row.excluded_games_insufficient_players ?? 0),
    included_players: Number(row.included_players ?? 0),
    earliest_game_date: row.earliest_game_date ? String(row.earliest_game_date) : null,
    latest_game_date: row.latest_game_date ? String(row.latest_game_date) : null,
  }));
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?:
    | { region?: string | string[] }
    | Promise<{ region?: string | string[] }>;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const [{ data: regionsData }, validityRows] = await Promise.all([
    supabase
      .from("regional_elo_regions")
      .select("region_type, region_key, player_count, updated_at")
      .eq("region_type", "state")
      .order("region_key", { ascending: true }),
    fetchRegionalValidity(),
  ]);

  const regions = (regionsData ?? []) as RegionRow[];
  const requestedRegion = decodeURIComponent(readRegionParam(resolvedSearchParams)).trim();
  const defaultRegion = regions.find((region) => region.region_key === "CALIFORNIA")?.region_key;
  const selectedRegion =
    regions.find((region) => region.region_key === requestedRegion)?.region_key ||
    regions.find((region) => region.region_key.toUpperCase() === requestedRegion.toUpperCase())
      ?.region_key ||
    defaultRegion ||
    regions[0]?.region_key;

  const leaderboard = selectedRegion ? await fetchAllRegionalRows(selectedRegion) : [];

  const topdeckIds = leaderboard
    .map((row) => row.topdeck_id)
    .filter((value): value is string => Boolean(value));
  const latestByPlayer = await fetchLatestCommanders(topdeckIds);

  const updatedAt = regions.find((r) => r.region_key === selectedRegion)?.updated_at ?? null;
  const globalValidity = validityRows.find((row) => row.scope === "global");
  const selectedRegionValidity = validityRows.find(
    (row) => row.scope === "region" && row.region_key === selectedRegion
  );
  const hasValidityData = validityRows.length > 0;
  const includedCoverage =
    globalValidity && globalValidity.total_games > 0
      ? globalValidity.included_games / globalValidity.total_games
      : 0;
  const selectedRegionCoverage =
    selectedRegionValidity && selectedRegionValidity.total_games > 0
      ? selectedRegionValidity.included_games / selectedRegionValidity.total_games
      : 0;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="knd-chip">Regional Elo</p>
              <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">State Leaderboards</h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/">
                Home
              </Link>
              <Link className="transition hover:text-foreground" href="/tournament-likelihood">
                Tournament Prep
              </Link>
              <Link className="transition hover:text-foreground" href="/midseason-invitational">
                MidSeason
              </Link>
              <Link className="transition hover:text-foreground" href="/about">
                Elo methodology
              </Link>
            </nav>
          </div>
          <p className="max-w-4xl text-base text-muted-foreground">
            Elo ratings recalculated within each state using only games played in that state.
            Players can rank differently across regions based on localized metas.
          </p>
          <p className="text-sm text-muted-foreground">
            Rating model details:{" "}
            <Link href="/methodology/elo" className="text-primary hover:text-foreground">
              cEDH Elo methodology
            </Link>
          </p>
        </header>

        <div className="mt-8 space-y-6">
          <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)_minmax(0,1fr)]">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Region</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <RegionSelector regions={regions} selectedRegion={selectedRegion} />
                <div className="text-xs text-muted-foreground">
                  Updated {updatedAt ? formatDate(updatedAt) : "—"}
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Global Validity
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Regional Elo only counts games from tournaments with populated state metadata and excludes pods with byes.
                </p>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                {!hasValidityData ? (
                  <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-3 text-xs text-muted-foreground">
                    Validity stats are unavailable in this deployment. The backend view
                    <span className="mx-1 font-mono text-foreground">regional_elo_data_validity</span>
                    likely has not been applied yet.
                  </div>
                ) : null}
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Included games</span>
                  <span className="font-mono text-foreground">
                    {globalValidity
                      ? `${globalValidity.included_games.toLocaleString()} / ${globalValidity.total_games.toLocaleString()}`
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Coverage rate</span>
                  <span className="font-mono text-primary">
                    {globalValidity ? formatPercent(includedCoverage) : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Missing state tournaments</span>
                  <span className="font-mono text-foreground">
                    {globalValidity ? globalValidity.tournaments_missing_state.toLocaleString() : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Games dropped for byes</span>
                  <span className="font-mono text-foreground">
                    {globalValidity ? globalValidity.excluded_games_with_byes.toLocaleString() : "—"}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  {selectedRegion ?? "Selected Region"}
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Region-specific sample quality for the active leaderboard.
                </p>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Ranked players</span>
                  <span className="font-mono text-foreground">
                    {(regions.find((row) => row.region_key === selectedRegion)?.player_count ?? 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Tracked tournaments</span>
                  <span className="font-mono text-foreground">
                    {selectedRegionValidity ? selectedRegionValidity.total_tournaments.toLocaleString() : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Included games</span>
                  <span className="font-mono text-foreground">
                    {selectedRegionValidity ? selectedRegionValidity.included_games.toLocaleString() : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Games dropped for byes</span>
                  <span className="font-mono text-foreground">
                    {selectedRegionValidity
                      ? selectedRegionValidity.excluded_games_with_byes.toLocaleString()
                      : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <span className="text-muted-foreground">Sample freshness</span>
                  <span className="font-mono text-foreground">
                    {selectedRegionValidity ? formatDate(selectedRegionValidity.latest_game_date) : "—"}
                  </span>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-3 text-xs text-muted-foreground">
                  {!hasValidityData
                    ? "This panel will populate after the regional validity migration is applied to the deployed database."
                    : selectedRegionValidity
                    ? `${formatPercent(selectedRegionCoverage)} of tracked ${selectedRegion} games currently qualify for regional Elo.`
                    : "No validity summary available for this region yet."}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                Top Players
              </CardTitle>
              <p className="text-xs text-muted-foreground">Active region: {selectedRegion ?? "—"}</p>
            </CardHeader>
            <CardContent>
              <div className="max-h-[70vh] overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <tr>
                      <th className="px-2 py-3">Rank</th>
                      <th className="px-2 py-3">Player</th>
                      <th className="px-2 py-3">Elo</th>
                      <th className="px-2 py-3">Games</th>
                      <th className="px-2 py-3">W-L-D</th>
                      <th className="px-2 py-3">Latest</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((row) => {
                      const topdeckHref = buildTopdeckProfileHref(row.topdeck_id);
                      const latestCommander = row.topdeck_id
                        ? latestByPlayer.get(row.topdeck_id)
                        : undefined;
                      return (
                        <tr key={row.player_id} className="border-t border-border/60">
                          <td className="px-2 py-3 text-muted-foreground">#{row.rank}</td>
                          <td className="px-2 py-3">
                            {row.topdeck_id ? (
                              <div className="space-y-1">
                                <Link
                                  className="font-medium text-foreground hover:text-primary"
                                  href={`/regional-elo/player/${row.topdeck_id}?region=${encodeURIComponent(selectedRegion ?? "")}`}
                                >
                                {row.player_name}
                                </Link>
                                {topdeckHref ? (
                                  <a
                                    className="inline-flex items-center rounded-md border border-border/60 px-2 py-1 text-[11px] font-medium text-muted-foreground hover:border-primary/40 hover:text-foreground"
                                    href={topdeckHref}
                                    rel="noreferrer"
                                    target="_blank"
                                  >
                                    TopDeck
                                  </a>
                                ) : null}
                              </div>
                            ) : (
                              <div className="font-medium text-foreground">{row.player_name}</div>
                            )}
                          </td>
                          <td className="px-2 py-3 font-semibold text-primary">{Math.round(row.rating)}</td>
                          <td className="px-2 py-3 text-muted-foreground">{row.games_played}</td>
                          <td className="px-2 py-3 text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                          <td className="px-2 py-3 text-xs text-muted-foreground">
                            <div>{formatDate(row.last_game_date)}</div>
                            <div className="truncate text-[11px]">
                              {latestCommander?.commander_name || "No commander data"}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {leaderboard.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-sm text-muted-foreground">
                          No regional Elo data yet. Run the regional Elo job to populate this leaderboard.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
