import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { COMMANDER_FALLBACK_LOOKBACK_MONTHS, COMMANDER_PRIMARY_LOOKBACK_MONTHS, lookbackStartDate } from "@/lib/meta-prep";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { extractTournamentSlug } from "@/lib/topdeck";
import Link from "next/link";
import { FieldShareList } from "./field-share-list";
import { TournamentAnalysisTables } from "./tournament-analysis-tables";
import { getTournamentAnalysis, fetchBestEloRows } from "./tournament-analysis";
import type { TournamentStanding, EloRow } from "./tournament-analysis";

export const dynamic = "force-dynamic";
const DEFAULT_LOOKBACK_MONTHS = COMMANDER_PRIMARY_LOOKBACK_MONTHS;

function buildTopdeckTournamentUrl(slug: string) {
  return slug ? `https://topdeck.gg/bracket/${slug}` : null;
}

function readStringParam(
  params:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | undefined,
  key: string
) {
  if (!params) return "";
  if (typeof (params as URLSearchParams).get === "function") {
    return (params as URLSearchParams).get(key) ?? "";
  }
  const value = (params as Record<string, string | string[] | undefined>)[key];
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function readStartTimestamp(startDate: string | number | null | undefined) {
  if (typeof startDate === "number") return startDate * 1000;
  if (!startDate) return null;
  const timestamp = Date.parse(startDate);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function formatStartTime(startDate: string | number | null | undefined) {
  const timestamp = readStartTimestamp(startDate);
  if (timestamp === null) return "Unknown start time";
  return new Date(timestamp).toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function hasTournamentStarted(startDate: string | number | null | undefined) {
  const timestamp = readStartTimestamp(startDate);
  return timestamp !== null && Date.now() >= timestamp;
}

export default async function TournamentLikelihoodPage({
  searchParams,
}: {
  searchParams?:
    | Promise<{ tournament?: string }>
    | { tournament?: string };
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const tournamentInput = readStringParam(resolvedSearchParams, "tournament").trim();
  const slug = extractTournamentSlug(tournamentInput);
  const lookbackMonths = DEFAULT_LOOKBACK_MONTHS;

  let tournament:
    | {
        name: string;
        game: string;
        format: string;
        startDate: string | number;
      }
    | null = null;
  let standings: TournamentStanding[] = [];
  let profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } = {
    players: [],
    metaShare: [],
  };
  let eloRows: EloRow[] = [];
  let hasRounds = false;
  let standingsAvailable = false;
  let updatedAt: string | null = null;
  let errorMessage: string | null = null;

  const { data: suggestedTournaments } = await supabase
    .from("tournaments")
    .select("topdeck_tid, name")
    .or("tier.eq.Platinum,tier.eq.Diamond,name.ilike.%Platinum%,topdeck_tid.ilike.%Platinum%,player_count.gte.100")
    .gte("start_date", new Date().toISOString())
    .order("start_date", { ascending: true })
    .limit(6);

  if (slug) {
    try {
      const analysis = await getTournamentAnalysis(slug, lookbackMonths);
      tournament = analysis.tournament;
      standings = analysis.standings;
      profiles = analysis.profiles;
      const latestStandingNameById = new Map(standings.map((standing) => [standing.id, standing.name]));
      eloRows = (await fetchBestEloRows(standings.map((standing) => standing.id).filter(Boolean))).map((row) => ({
        ...row,
        player_name: row.topdeck_id ? latestStandingNameById.get(row.topdeck_id) ?? row.player_name : row.player_name,
      }));
      hasRounds = analysis.hasRounds;
      standingsAvailable = analysis.standingsAvailable;
      updatedAt = analysis.updatedAt;
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  const playersWithData = profiles.players.filter((player) => player.totalEntries > 0).length;
  const tournamentHasStarted = tournament ? hasTournamentStarted(tournament.startDate) : false;
  const hasTournamentResults = standingsAvailable && hasRounds;
  const lookbackStartTimestamp = tournamentHasStarted && tournament
    ? readStartTimestamp(tournament.startDate)
    : null;
  const lookbackStart = lookbackStartDate(
    lookbackMonths,
    lookbackStartTimestamp ? new Date(lookbackStartTimestamp) : new Date()
  );

  const weightedMeta = new Map<string, number>();
  for (const player of profiles.players) {
    for (const commander of player.commanders.slice(0, 3)) {
      weightedMeta.set(
        commander.commander,
        (weightedMeta.get(commander.commander) ?? 0) + commander.predictionShare
      );
    }
  }
  const weightedMetaRows = Array.from(weightedMeta.entries())
    .map(([commander, expectedPlayers]) => ({
      commander,
      fieldShare: standings.length ? expectedPlayers / standings.length : 0,
      expectedPlayers,
    }))
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers);

  const actualMeta = new Map<string, number>();
  for (const standing of standings) {
    if (!standing.actualDeckCommander) continue;
    actualMeta.set(standing.actualDeckCommander, (actualMeta.get(standing.actualDeckCommander) ?? 0) + 1);
  }
  const actualMetaRows = Array.from(actualMeta.entries())
    .map(([commander, players]) => ({
      commander,
      fieldShare: standings.length ? players / standings.length : 0,
      expectedPlayers: players,
    }))
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers);

  const showActualDecks = hasTournamentResults && actualMetaRows.length > 0;
  const fieldShareRows = showActualDecks ? actualMetaRows : weightedMetaRows;
  const topCommander = fieldShareRows[0];
  const topFiveCombinedShare = fieldShareRows
    .slice(0, 5)
    .reduce((sum, row) => sum + row.fieldShare, 0);
  const tournamentHref = buildTopdeckTournamentUrl(slug);

  const profileByPlayer = new Map(profiles.players.map((player) => [player.topdeckId, player]));
  const standingByPlayer = new Map(standings.map((player) => [player.id, player]));
  const allTopEloAttendees = eloRows
    .map((row) => ({
      ...row,
      standing: row.topdeck_id ? standingByPlayer.get(row.topdeck_id) : undefined,
      profile: row.topdeck_id ? profileByPlayer.get(row.topdeck_id) : undefined,
    }));

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div>
            <p className="knd-chip">Tournament Prep</p>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Pre-Tournament Meta Scouting
            </h1>
          </div>
          <p className="max-w-4xl text-base text-muted-foreground">
            Paste any TopDeck tournament link or slug to profile the attendees by their recent
            commander history and estimate the likely field.
          </p>
        </header>

        <Card className="knd-panel mt-8">
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
              Tournament Input
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 lg:grid-cols-[1fr_auto]" method="get">
              <label className="flex flex-col gap-2 text-sm text-muted-foreground">
                TopDeck tournament link or slug
                <input
                  className="knd-input"
                  defaultValue={tournamentInput}
                  name="tournament"
                  placeholder="https://topdeck.gg/event/... or slug"
                  type="text"
                />
              </label>
              <div className="flex items-end">
                <button className="knd-chip border border-border/70 px-4 py-3 text-sm text-foreground" type="submit">
                  Analyze Tournament
                </button>
              </div>
            </form>
            <p className="mt-4 text-sm text-muted-foreground">
              The model uses players in the selected event, looks up their known commander entries
              since {lookbackStart}, then estimates likely deck choice from their recent history.
              Players with sparse recent history fall back to a {COMMANDER_FALLBACK_LOOKBACK_MONTHS}-month window.
            </p>

            <div className="mt-6 border-t border-border/60 pt-6">
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground mb-3">Suggested Platinum & Large Events</p>
              <div className="flex flex-wrap gap-2">
                {suggestedTournaments?.map((t) => (
                  <Link 
                    key={t.topdeck_tid}
                    href={`/tournament-likelihood?tournament=${t.topdeck_tid}`}
                    className="knd-chip border border-border/60 bg-muted/20 px-3 py-2 text-xs hover:border-primary/40 hover:bg-muted/40 transition"
                  >
                    {t.name}
                  </Link>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {!tournamentInput && (
          <Card className="knd-panel mt-6">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                Ready
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Enter a TopDeck link to build player deck profiles and an expected field share for that tournament.
            </CardContent>
          </Card>
        )}

        {tournamentInput && !slug && (
          <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            Could not parse a tournament slug from that input. Paste a TopDeck event/bracket URL or a raw slug.
          </div>
        )}

        {errorMessage && (
          <div className="mt-6 rounded-md border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200">
            Failed to analyze tournament: {errorMessage}
          </div>
        )}

        {updatedAt && !errorMessage && (
          <p className="mt-6 text-sm text-muted-foreground">
            Checked <time dateTime={updatedAt}>{new Date(updatedAt).toLocaleTimeString("en-GB", { timeZone: "UTC" })} UTC</time>.
          </p>
        )}
        {tournament && !standingsAvailable && !errorMessage && (
          <p role="status" className="mt-4 text-sm text-muted-foreground">
            Live standings are unavailable. Showing attendees and deck forecasts only. Check the event on TopDeck for current results.
          </p>
        )}
        {hasTournamentResults && !showActualDecks && !errorMessage && (
          <p className="mt-4 text-sm text-muted-foreground">
            Standings are current, but submitted commanders are not available. Deck choices below remain forecasts.
          </p>
        )}
        {tournament && !errorMessage && (
          <>
            <Card className="knd-panel mt-6">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Tournament Snapshot
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-md border border-border/60 bg-muted/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Tournament</p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {tournamentHref ? (
                      <a href={tournamentHref} target="_blank" rel="noreferrer" className="hover:text-primary">
                        {tournament.name}
                      </a>
                    ) : (
                      tournament.name
                    )}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {tournament.format} | {formatStartTime(tournament.startDate)}
                  </p>
                </div>
                <div className="rounded-md border border-border/60 bg-muted/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Attendees</p>
                  <p className="mt-2 text-lg font-semibold text-foreground">{standings.length}</p>
                  <p className="mt-1 text-sm text-muted-foreground">Players found on TopDeck</p>
                </div>
                <div className="rounded-md border border-border/60 bg-muted/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Coverage</p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {playersWithData}/{standings.length}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {standings.length ? formatPercent(playersWithData / standings.length) : "0%"} with recent deck data
                  </p>
                </div>
                <div className="rounded-md border border-border/60 bg-muted/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    {showActualDecks ? "Most Played Deck" : "Most Likely Deck"}
                  </p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {topCommander ? `${topCommander.commander} (${formatPercent(topCommander.fieldShare)})` : "No consensus yet"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Top 5 commanders represent {formatPercent(topFiveCombinedShare)} of{" "}
                    {showActualDecks ? "the full field" : "known field history"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel mt-6">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  {showActualDecks ? "Field Share" : "Expected Field Share (Player-Weighted)"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 text-sm text-muted-foreground">
                  {showActualDecks ? (
                    "Actual submitted commander choices from this tournament."
                  ) : (
                    "This estimate weights each player by how concentrated their recent commander usage is."
                  )}
                </div>
                <FieldShareList rows={fieldShareRows} hasTournamentResults={showActualDecks} />
              </CardContent>
            </Card>

            <TournamentAnalysisTables
              key={`${slug}-${hasTournamentResults}`}
              eloAttendees={allTopEloAttendees}
              showActualDecks={showActualDecks}
              showTournamentRecord={hasTournamentResults}
              profiles={profiles.players}
              standings={standings}
            />
          </>
        )}
      </main>
    </div>
  );
}
