import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import Link from "next/link";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";

export const dynamic = "force-dynamic";

function readMonthsParam(
  params: Awaited<Promise<{ months?: string }> | { months?: string }> | undefined
) {
  const anyParams = params as
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined;
  if (!anyParams) return undefined;
  if (typeof (anyParams as URLSearchParams).get === "function") {
    return (anyParams as URLSearchParams).get("months") ?? undefined;
  }
  const value = (anyParams as Record<string, string | string[] | undefined>).months;
  return Array.isArray(value) ? value[0] : value;
}

export default async function MidseasonInvitationalPage({
  searchParams,
}: {
  searchParams?: Promise<{ months?: string }> | { months?: string };
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const months = Number(readMonthsParam(resolvedSearchParams) || "12");
  const lookbackMonths = Number.isFinite(months) && months > 0 ? months : 12;
  const lookbackStart = lookbackStartDate(lookbackMonths);

  let errorMessage: string | null = null;
  let top100: Awaited<ReturnType<typeof fetchChampionshipLeaderboard>> = [];
  let profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } = {
    players: [],
    metaShare: [],
  };
  try {
    const leaderboard = (await fetchChampionshipLeaderboard()).sort((a, b) => a.rank - b.rank);
    top100 = leaderboard.slice(0, 100);
  } catch (error) {
    errorMessage = (error as Error).message;
  }

  if (top100.length > 0) {
    try {
      const topdeckIds = top100.map((entry) => entry.uid);
      const usageRows = await getCommanderUsageRows(topdeckIds, lookbackStart);
      profiles = buildProfiles(topdeckIds, usageRows, 3);
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  const playersWithData = profiles.players.filter((player) => player.totalEntries > 0).length;
  const topDeckShares = profiles.players
    .filter((player) => player.commanders.length > 0)
    .map((player) => player.commanders[0]?.share ?? 0);
  const avgTopDeckShare = topDeckShares.length
    ? topDeckShares.reduce((sum, share) => sum + share, 0) / topDeckShares.length
    : 0;
  const topFiveCombinedShare = profiles.metaShare
    .slice(0, 5)
    .reduce((sum, row) => sum + row.share, 0);
  const topCommander = profiles.metaShare[0];
  const totalInvitedPlayers = top100.length;
  const weightedMeta = new Map<string, number>();
  for (const player of profiles.players) {
    for (const commander of player.commanders) {
      weightedMeta.set(
        commander.commander,
        (weightedMeta.get(commander.commander) ?? 0) + commander.weightedShare
      );
    }
  }
  const weightedMetaRows = Array.from(weightedMeta.entries())
    .map(([commander, expectedPlayers]) => ({
      commander,
      fieldShare: totalInvitedPlayers ? expectedPlayers / totalInvitedPlayers : 0,
      expectedPlayers,
    }))
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers)
    .slice(0, 15);

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="knd-chip">MidSeason Invitational</p>
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
              Back to Home
            </Link>
          </div>
          <h1 className="text-4xl font-semibold text-foreground">Top 100 Player Deck Profiles</h1>
          <p className="text-base text-muted-foreground">
            TopDeck Championship Series leaderboard (top 100) with each player’s most common
            commanders from the last {lookbackMonths} months.
          </p>
        </div>

        <Card className="knd-panel mt-8">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Expected Field Share (Player-Weighted)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-4 text-sm text-muted-foreground">
              Consensus snapshot for invited players based on recent known commander entries
              (Unknown Commander omitted). Percentages are weighted by player-level commander
              usage across the 100-player invite field.
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {weightedMetaRows.map((row) => (
                <div key={row.commander} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{row.commander}</span>
                  <span className="text-primary">{Math.round(row.fieldShare * 100)}%</span>
                </div>
              ))}
              {!weightedMetaRows.length && (
                <div className="text-sm text-muted-foreground">No commander history for leaderboard.</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="knd-panel mt-6">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Consensus Snapshot
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="rounded-md border border-border/60 bg-muted/20 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Coverage
              </p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {playersWithData}/{top100.length} invited players have recent deck data
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {top100.length
                  ? `${Math.round((playersWithData / top100.length) * 100)}% profile coverage`
                  : "No leaderboard data"}
              </p>
            </div>
            <div className="rounded-md border border-border/60 bg-muted/20 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Most Likely Deck
              </p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {topCommander
                  ? `${topCommander.commander} (${Math.round(topCommander.share * 100)}%)`
                  : "No deck consensus yet"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Top 5 commanders represent {Math.round(topFiveCombinedShare * 100)}% of expected
                field usage
              </p>
            </div>
            <div className="rounded-md border border-border/60 bg-muted/20 p-4 md:col-span-2">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Prep Read
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Average invited player top-deck concentration:{" "}
                <span className="text-foreground font-medium">
                  {Math.round(avgTopDeckShare * 100)}%
                </span>
                . Higher values suggest more stable pilot/deck pairings; lower values suggest more
                switching and broader prep targets.
              </p>
            </div>
          </CardContent>
        </Card>

        {errorMessage && (
          <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            Failed to load TopDeck leaderboard: {errorMessage}
          </div>
        )}

        <Card className="knd-panel mt-6">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Player Commander Profiles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-[0.3em] text-muted-foreground">
                  <tr>
                    <th className="px-2 py-3">Rank</th>
                    <th className="px-2 py-3">Player</th>
                    <th className="px-2 py-3">Points</th>
                    <th className="px-2 py-3">Most Common Decks</th>
                  </tr>
                </thead>
                <tbody>
                  {top100.map((entry) => {
                    const profile = profiles.players.find((p) => p.topdeckId === entry.uid);
                    const profileHref = buildTopdeckProfileHref(entry.username || entry.uid);
                    return (
                      <tr key={entry.uid} className="border-t border-border/60">
                        <td className="px-2 py-4 text-muted-foreground">#{entry.rank}</td>
                        <td className="px-2 py-4">
                          {profileHref ? (
                            <a
                              className="font-medium text-foreground hover:text-primary"
                              href={profileHref}
                              rel="noreferrer"
                              target="_blank"
                            >
                              {entry.name}
                            </a>
                          ) : (
                            <div className="font-medium text-foreground">{entry.name}</div>
                          )}
                          <div className="text-xs text-muted-foreground">{entry.username || entry.uid}</div>
                        </td>
                        <td className="px-2 py-4 text-muted-foreground">{entry.points}</td>
                        <td className="px-2 py-4">
                          <div className="flex flex-wrap gap-2">
                            {profile?.commanders?.length ? (
                              profile.commanders.map((commander) => (
                                <span
                                  key={`${entry.uid}-${commander.commander}`}
                                  className="knd-chip"
                                >
                                  {commander.commander} · {Math.round(commander.share * 100)}% (
                                  {commander.entries})
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">No recent data</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
