import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchTournamentBySlug } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";

export const dynamic = "force-dynamic";

const DEFAULT_TOURNAMENT = "cardart-monthly-underground-sea";

export default async function TournamentLikelihoodPage({
  searchParams,
}: {
  searchParams?: { tournament?: string; months?: string };
}) {
  const tournamentSlug = searchParams?.tournament || "";
  const months = Number(searchParams?.months || "12");
  const lookbackMonths = Number.isFinite(months) && months > 0 ? months : 12;

  let tournamentName = "";
  let tournamentDate = "";
  let attendees: Array<{ name: string; id: string; standing: number }> = [];
  let playerProfiles: ReturnType<typeof buildProfiles> | null = null;
  let errorMessage: string | null = null;

  if (tournamentSlug) {
    try {
      const tournament = await fetchTournamentBySlug(tournamentSlug);
      tournamentName = tournament.data?.name || tournamentSlug;
      tournamentDate = tournament.data?.startDate || "";
      attendees = (tournament.standings || [])
        .map((row) => ({
          name: row.name,
          id: row.id,
          standing: row.standing,
        }))
        .sort((a, b) => a.standing - b.standing);

      const topdeckIds = attendees.map((attendee) => attendee.id);
      const lookbackStart = lookbackStartDate(lookbackMonths);
      const usageRows = await getCommanderUsageRows(topdeckIds, lookbackStart);
      playerProfiles = buildProfiles(topdeckIds, usageRows, 3);
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="space-y-4">
          <p className="text-xs uppercase tracking-[0.4em] text-[#c9a227]">Tournament Likelihood</p>
          <h1 className="text-4xl font-semibold">Pre-Tournament Meta Scouting</h1>
          <p className="text-base text-zinc-300">
            Pull registered attendees from TopDeck.gg and map their historical commander usage using
            our Supabase archive. Use this to predict the likely meta share for an upcoming event.
          </p>
        </div>

        <Card className="mt-8 border border-[#2a2a2a] bg-[#111111]">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
              Tournament Selector
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 sm:grid-cols-[1fr_140px_120px]">
              <div className="space-y-2">
                <label className="text-sm text-zinc-300">TopDeck tournament slug</label>
                <input
                  name="tournament"
                  defaultValue={tournamentSlug || DEFAULT_TOURNAMENT}
                  placeholder={DEFAULT_TOURNAMENT}
                  className="w-full rounded-md border border-[#2a2a2a] bg-[#0f0f0f] px-3 py-2 text-sm text-white"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-zinc-300">Lookback (months)</label>
                <input
                  name="months"
                  type="number"
                  min={1}
                  defaultValue={lookbackMonths}
                  className="w-full rounded-md border border-[#2a2a2a] bg-[#0f0f0f] px-3 py-2 text-sm text-white"
                />
              </div>
              <div className="flex items-end">
                <button
                  className="w-full rounded-md bg-[#c9a227] px-3 py-2 text-sm font-semibold text-black"
                  type="submit"
                >
                  Generate
                </button>
              </div>
            </form>
          </CardContent>
        </Card>

        {errorMessage && (
          <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            {errorMessage}
          </div>
        )}

        {tournamentSlug && playerProfiles && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <Card className="border border-[#2a2a2a] bg-[#111111]">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
                  Attendee Commander Likelihood
                </CardTitle>
                <p className="text-sm text-zinc-500">
                  {tournamentName} · {tournamentDate ? new Date(tournamentDate).toDateString() : ""}
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {attendees.map((attendee) => {
                    const profile = playerProfiles.players.find((p) => p.topdeckId === attendee.id);
                    const commanders = profile?.commanders ?? [];
                    return (
                      <div key={attendee.id} className="border-b border-[#222222] pb-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-white">{attendee.name}</div>
                            <div className="text-xs text-zinc-500">TopDeck ID: {attendee.id}</div>
                          </div>
                          <div className="text-xs text-zinc-500">Standing #{attendee.standing}</div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {commanders.length ? (
                            commanders.map((commander) => (
                              <span
                                key={commander.commander}
                                className="rounded-full border border-[#2a2a2a] bg-[#0f0f0f] px-3 py-1 text-xs text-zinc-200"
                              >
                                {commander.commander} · {Math.round(commander.share * 100)}%
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-zinc-500">No recent data</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            <Card className="border border-[#2a2a2a] bg-[#111111]">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
                  Expected Meta Share
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {playerProfiles.metaShare.map((row) => (
                    <div key={row.commander} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-200">{row.commander}</span>
                      <span className="text-[#c9a227]">
                        {Math.round(row.share * 100)}% ({row.entries})
                      </span>
                    </div>
                  ))}
                  {!playerProfiles.metaShare.length && (
                    <div className="text-sm text-zinc-500">No commander history for attendees.</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
