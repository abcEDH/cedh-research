import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";

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
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-[0.4em] text-[#c9a227]">MidSeason Invitational</p>
          <h1 className="text-4xl font-semibold">Top 100 Player Deck Profiles</h1>
          <p className="text-base text-zinc-300">
            TopDeck Championship Series leaderboard (top 100) with each player’s most common
            commanders from the last {lookbackMonths} months.
          </p>
        </div>

        <Card className="mt-8 border border-[#2a2a2a] bg-[#111111]">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
              Expected Meta Share
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {profiles.metaShare.map((row) => (
                <div key={row.commander} className="flex items-center justify-between text-sm">
                  <span className="text-zinc-200">{row.commander}</span>
                  <span className="text-[#c9a227]">
                    {Math.round(row.share * 100)}% ({row.entries})
                  </span>
                </div>
              ))}
              {!profiles.metaShare.length && (
                <div className="text-sm text-zinc-500">No commander history for leaderboard.</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="mt-6 border border-[#2a2a2a] bg-[#111111]">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
              Player Commander Profiles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-[0.3em] text-zinc-500">
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
                      <tr key={entry.uid} className="border-t border-[#222222]">
                        <td className="py-3 text-zinc-400">#{entry.rank}</td>
                        <td className="py-3">
                          <div className="font-medium text-white">{entry.name}</div>
                          <div className="text-xs text-zinc-500">{entry.username || entry.uid}</div>
                        </td>
                        <td className="py-3 text-zinc-300">{entry.points}</td>
                        <td className="py-3">
                          <div className="flex flex-wrap gap-2">
                            {profile?.commanders?.length ? (
                              profile.commanders.map((commander) => (
                                <span
                                  key={`${entry.uid}-${commander.commander}`}
                                  className="rounded-full border border-[#2a2a2a] bg-[#0f0f0f] px-3 py-1 text-xs text-zinc-200"
                                >
                                  {commander.commander} · {Math.round(commander.share * 100)}%
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-zinc-500">No recent data</span>
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
      </div>
    </div>
  );
}
