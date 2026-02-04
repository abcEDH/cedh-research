import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchTournamentBySlug } from "@/lib/topdeck";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import Link from "next/link";

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
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="knd-chip">Tournament Prep</p>
              <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
                Pre-Tournament Meta Scouting
              </h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/">
                Home
              </Link>
              <Link className="transition hover:text-foreground" href="/regional-elo">
                Regional Elo
              </Link>
              <Link className="transition hover:text-foreground" href="/midseason-invitational">
                MidSeason
              </Link>
            </nav>
          </div>
          <p className="max-w-4xl text-base text-muted-foreground">
            Pull registered attendees from TopDeck.gg and map their historical commander usage using
            our Supabase archive. Use this to predict the likely meta share for an upcoming event.
          </p>
        </header>

        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Example slug: <code className="text-primary">{DEFAULT_TOURNAMENT}</code> from{" "}
            <a
              className="text-primary underline decoration-primary/40 underline-offset-4"
              href="https://topdeck.gg/bracket/cardart-monthly-underground-sea"
              rel="noreferrer"
              target="_blank"
            >
              TopDeck bracket page
            </a>
          </p>
        </div>

        <Card className="knd-panel mt-8">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Tournament Selector
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form action="/tournament-likelihood" method="get" className="grid gap-4 sm:grid-cols-[1fr_140px_120px]">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">TopDeck tournament slug</label>
                <input
                  name="tournament"
                  defaultValue={tournamentSlug || DEFAULT_TOURNAMENT}
                  placeholder={DEFAULT_TOURNAMENT}
                  className="knd-input"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Lookback (months)</label>
                <input
                  name="months"
                  type="number"
                  min={1}
                  defaultValue={lookbackMonths}
                  className="knd-input"
                />
              </div>
              <div className="flex items-end">
                <Button className="w-full" type="submit">
                  Generate
                </Button>
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
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-zinc-400">
                  Attendee Commander Likelihood
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {tournamentName} · {tournamentDate ? new Date(tournamentDate).toDateString() : ""}
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {attendees.map((attendee) => {
                    const profile = playerProfiles.players.find((p) => p.topdeckId === attendee.id);
                    const commanders = profile?.commanders ?? [];
                    return (
                      <div key={attendee.id} className="border-b border-border/60 pb-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-semibold text-white">{attendee.name}</div>
                            <div className="text-xs text-muted-foreground">TopDeck ID: {attendee.id}</div>
                          </div>
                          <div className="text-xs text-muted-foreground">Standing #{attendee.standing}</div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {commanders.length ? (
                            commanders.map((commander) => (
                              <span
                                key={commander.commander}
                                className="knd-chip"
                              >
                                {commander.commander} · {Math.round(commander.share * 100)}%
                              </span>
                            ))
                          ) : (
                            <span className="text-xs text-muted-foreground">No recent data</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Expected Meta Share
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {playerProfiles.metaShare.map((row) => (
                    <div key={row.commander} className="flex items-center justify-between text-sm">
                      <span className="text-foreground">{row.commander}</span>
                      <span className="text-primary">
                        {Math.round(row.share * 100)}% ({row.entries})
                      </span>
                    </div>
                  ))}
                  {!playerProfiles.metaShare.length && (
                    <div className="text-sm text-muted-foreground">No commander history for attendees.</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </main>
    </div>
  );
}
