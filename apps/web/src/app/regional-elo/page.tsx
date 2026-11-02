import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EloGameFilter } from "@/components/elo-game-filter";
import {
  LEADERBOARD_PAGE_SIZE,
  loadRegionalEloData,
  type RegionalEloSearchParams,
} from "@/lib/regional-elo/fetchers";
import { RegionalLeaderboardTable } from "./regional-leaderboard-table";
import { RegionSelector } from "./region-selector";

export const dynamic = "force-dynamic";
export { toClientLeaderboardRow } from "@/lib/regional-elo/fetchers";

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function buildLeaderboardFilterHref({
  selectedScope,
  selectedCountry,
  selectedRegion,
  playerSearch,
  page,
  eloOnly,
}: {
  selectedScope: "global" | "country";
  selectedCountry?: string;
  selectedRegion?: string;
  playerSearch: string;
  page: number;
  eloOnly: boolean;
}) {
  const params = new URLSearchParams();
  params.set("scope", selectedScope);
  if (selectedScope === "country" && selectedCountry)
    params.set("country", selectedCountry);
  if (selectedScope === "country" && selectedRegion)
    params.set("region", selectedRegion);
  if (playerSearch) params.set("q", playerSearch);
  if (page > 1) params.set("page", String(page));
  if (!eloOnly) params.set("eloOnly", "false");
  const query = params.toString();
  return `/regional-elo${query ? `?${query}` : ""}`;
}

export default async function RegionalEloPage({
  searchParams,
}: {
  searchParams?: RegionalEloSearchParams | Promise<RegionalEloSearchParams>;
}) {
  const data = await loadRegionalEloData(await Promise.resolve(searchParams));
  const {
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
  } = data;
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[1fr_350px] xl:items-start xl:gap-12">
            <div className="flex flex-col gap-4">
              <div>
                <h1 className="text-3xl font-semibold text-foreground md:text-4xl">
                  Global Leaderboard
                </h1>
              </div>
              <p className="text-base text-muted-foreground">
                TopDeck Elo is shown for players with a published TopDeck Elo
                snapshot. Country and state views are filtered slices of the
                local active player set.
              </p>
              <p className="text-sm text-muted-foreground">
                Rating model details:{" "}
                <Link
                  href="/methodology/elo"
                  className="text-primary hover:text-foreground"
                >
                  cEDH Elo methodology
                </Link>
              </p>
            </div>
            <Card className="knd-panel w-full">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Region
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <RegionSelector
                  regions={regions}
                  selectedScope={selectedScope}
                  selectedCountry={selectedCountry}
                  selectedRegion={selectedRegion}
                  supportsCountryRegions={hasCountryOptions}
                  eloOnly={eloOnly}
                />
                <div className="text-xs text-muted-foreground">
                  Updated {updatedAt ? formatDate(updatedAt) : "—"}
                </div>
              </CardContent>
            </Card>
          </div>
        </header>
        <div className="mt-8 space-y-6">
          <EloGameFilter
            eloOnly={eloOnly}
            allGamesHref={buildLeaderboardFilterHref({
              selectedScope,
              selectedCountry,
              selectedRegion,
              playerSearch,
              page: currentPage,
              eloOnly: false,
            })}
            rankingGamesHref={buildLeaderboardFilterHref({
              selectedScope,
              selectedCountry,
              selectedRegion,
              playerSearch,
              page: currentPage,
              eloOnly: true,
            })}
          />
          <Card className="knd-panel">
            <CardHeader className="gap-4 md:flex-row md:items-end md:justify-between">
              <div className="space-y-2">
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Top Players
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Active view:{" "}
                  {activeRegionType === "global"
                    ? "Global"
                    : activeRegionKey || "—"}
                </p>
              </div>
              <form
                action="/regional-elo"
                method="get"
                className="flex w-full flex-col gap-2 md:max-w-sm md:flex-row"
              >
                <input type="hidden" name="scope" value={selectedScope} />
                {selectedScope === "country" && selectedCountry ? (
                  <input type="hidden" name="country" value={selectedCountry} />
                ) : null}
                {selectedScope === "country" && selectedRegion ? (
                  <input type="hidden" name="region" value={selectedRegion} />
                ) : null}
                <input type="hidden" name="page" value="1" />
                <input
                  type="hidden"
                  name="eloOnly"
                  value={eloOnly ? "true" : "false"}
                />
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
                latestByPlayer={latestByPlayer}
                leaderboard={leaderboard}
                currentPage={currentPage}
                totalCount={leaderboardPage.totalCount}
                pageSize={LEADERBOARD_PAGE_SIZE}
                selectedScope={selectedScope}
                selectedCountry={selectedCountry}
                selectedRegion={selectedRegion}
                playerSearch={playerSearch}
                eloOnly={eloOnly}
              />
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
