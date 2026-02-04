import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { RegionSelector } from "./region-selector";

export const dynamic = "force-dynamic";

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

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?:
    | { region?: string | string[] }
    | Promise<{ region?: string | string[] }>;
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const { data: regionsData } = await supabase
    .from("regional_elo_regions")
    .select("region_type, region_key, player_count, updated_at")
    .eq("region_type", "state")
    .order("region_key", { ascending: true });

  const regions = (regionsData ?? []) as RegionRow[];
  const regionParam = Array.isArray(resolvedSearchParams?.region)
    ? resolvedSearchParams?.region[0]
    : resolvedSearchParams?.region;
  const requestedRegion = decodeURIComponent(regionParam ?? "").trim();
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
            Elo ratings recalculated within each state using only local games. Players can rank
            differently across regions based on localized metas.
          </p>
        </header>

        <div className="mt-8 grid gap-6 lg:grid-cols-[280px_1fr]">
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
                      <th className="px-2 py-3">W-D-L</th>
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
                            {topdeckHref ? (
                              <a
                                className="font-medium text-foreground hover:text-primary"
                                href={topdeckHref}
                                rel="noreferrer"
                                target="_blank"
                              >
                                {row.player_name}
                              </a>
                            ) : (
                              <div className="font-medium text-foreground">{row.player_name}</div>
                            )}
                          </td>
                          <td className="px-2 py-3 font-semibold text-primary">{Math.round(row.rating)}</td>
                          <td className="px-2 py-3 text-muted-foreground">{row.games_played}</td>
                          <td className="px-2 py-3 text-muted-foreground">
                            {row.wins}-{row.draws}-{row.losses}
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
