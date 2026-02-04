import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import Link from "next/link";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";

export const dynamic = "force-dynamic";

export default async function MidseasonInvitationalPage({
  searchParams,
}: {
  searchParams?: { months?: string };
}) {
  const months = Number(searchParams?.months || "12");
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
    const topdeckIds = top100.map((entry) => entry.uid);
    const usageRows = await getCommanderUsageRows(topdeckIds, lookbackStart);
    profiles = buildProfiles(topdeckIds, usageRows, 3);
  } catch (error) {
    errorMessage = (error as Error).message;
  }

  const totalInvitedPlayers = top100.length;
  const knownProfiles = profiles.players.filter((player) => player.totalEntries > 0);
  const weightedMeta = new Map<string, number>();
  for (const player of profiles.players) {
    for (const commander of player.commanders) {
      weightedMeta.set(
        commander.commander,
        (weightedMeta.get(commander.commander) ?? 0) + commander.share
      );
    }
  }
  const weightedMetaRows = Array.from(weightedMeta.entries())
    .map(([commander, expectedPlayers]) => ({
      commander,
      expectedPlayers,
      fieldShare: totalInvitedPlayers ? expectedPlayers / totalInvitedPlayers : 0,
      knownShare: knownProfiles.length ? expectedPlayers / knownProfiles.length : 0,
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
              usage and measured against the 100-player invite field.
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {weightedMetaRows.map((row) => (
                <div key={row.commander} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{row.commander}</span>
                  <span className="text-primary">
                    {Math.round(row.fieldShare * 100)}% field · {Math.round(row.knownShare * 100)}%
                    known ({row.expectedPlayers.toFixed(1)})
                  </span>
                </div>
              ))}
              {!weightedMetaRows.length && (
                <div className="text-sm text-muted-foreground">No commander history for leaderboard.</div>
              )}
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
                                  {commander.commander} · {Math.round(commander.share * 100)}%
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
