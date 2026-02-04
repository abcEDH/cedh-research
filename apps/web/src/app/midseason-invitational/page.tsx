import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function MidseasonInvitationalPage({
  searchParams,
}: {
  searchParams?: { months?: string };
}) {
  const months = Number(searchParams?.months || "12");
  const lookbackMonths = Number.isFinite(months) && months > 0 ? months : 12;
  const lookbackStart = lookbackStartDate(lookbackMonths);

  const leaderboard = (await fetchChampionshipLeaderboard()).sort((a, b) => a.rank - b.rank);
  const top100 = leaderboard.slice(0, 100);
  const topdeckIds = top100.map((entry) => entry.uid);

  const usageRows = await getCommanderUsageRows(topdeckIds, lookbackStart);
  const profiles = buildProfiles(topdeckIds, usageRows, 3);

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
              Expected Meta Share
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {profiles.metaShare.map((row) => (
                <div key={row.commander} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{row.commander}</span>
                  <span className="text-primary">
                    {Math.round(row.share * 100)}% ({row.entries})
                  </span>
                </div>
              ))}
              {!profiles.metaShare.length && (
                <div className="text-sm text-muted-foreground">No commander history for leaderboard.</div>
              )}
            </div>
          </CardContent>
        </Card>

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
                    <th className="py-2">Rank</th>
                    <th>Player</th>
                    <th>Points</th>
                    <th>Most Common Decks</th>
                  </tr>
                </thead>
                <tbody>
                  {top100.map((entry) => {
                    const profile = profiles.players.find((p) => p.topdeckId === entry.uid);
                    return (
                      <tr key={entry.uid} className="border-t border-border/60">
                        <td className="py-3 text-muted-foreground">#{entry.rank}</td>
                        <td className="py-3">
                          <div className="font-medium text-white">{entry.name}</div>
                          <div className="text-xs text-muted-foreground">{entry.username || entry.uid}</div>
                        </td>
                        <td className="py-3 text-muted-foreground">{entry.points}</td>
                        <td className="py-3">
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
