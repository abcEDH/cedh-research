import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { predictNextState, type PlayerStateHistoryRow } from "@/lib/player-region-predictor";
import { supabase } from "@/lib/supabase";
import {
  attachLatestDecklistUrls,
  buildProfiles,
  COMMANDER_FALLBACK_LOOKBACK_MONTHS,
  COMMANDER_PRIMARY_LOOKBACK_MONTHS,
  getCommanderDecklistRows,
  getCommanderUsageRows,
  lookbackStartDate,
  selectCommanderForecastRows,
} from "@/lib/meta-prep";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { extractTournamentSlug, fetchTournamentBySlug } from "@/lib/topdeck";
import Link from "next/link";
import { unstable_cache } from "next/cache";
import { TournamentAnalysisTables } from "./tournament-analysis-tables";

export const dynamic = "force-dynamic";
const DEFAULT_LOOKBACK_MONTHS = COMMANDER_PRIMARY_LOOKBACK_MONTHS;

type TournamentStanding = {
  name: string;
  id: string;
  username?: string | null;
  standing: number;
  points: number;
  winRate: number;
  opponentWinRate: number;
  wins: number;
  draws: number;
  losses: number;
  actualDeckCommander: string | null;
  actualDecklistUrl: string | null;
};

type EloRow = {
  topdeck_id: string | null;
  player_name: string;
  rating: number;
  games_played: number;
  region_key: string;
};

type RegionalLeaderboardQueryRow = {
  topdeck_id: string | null;
  player_name: string;
  rating: number;
  games_played: number;
  region_key: string;
  rank: number;
};

type PlayerStateHistoryQueryRow = {
  players:
    | {
        topdeck_id: string | null;
      }
    | Array<{
        topdeck_id: string | null;
      }>
    | null;
  tournaments:
    | {
        start_date: string | null;
        state: string | null;
        city: string | null;
        player_count: number | null;
      }
    | Array<{
        start_date: string | null;
        state: string | null;
        city: string | null;
        player_count: number | null;
      }>
    | null;
};

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

function firstRelation<T>(value: T | T[] | null) {
  return Array.isArray(value) ? value[0] ?? null : value;
}

async function fetchPredictedRegions(topdeckIds: string[]): Promise<Map<string, string>> {
  if (topdeckIds.length === 0) return new Map();

  const { data, error } = await supabase
    .from("tournament_entries")
    .select("players!inner(topdeck_id), tournaments!inner(start_date, state, city, player_count)")
    .in("players.topdeck_id", topdeckIds)
    .not("tournaments.state", "is", null)
    .not("tournaments.start_date", "is", null);

  if (error) {
    throw new Error(`Error fetching player regions: ${error.message}`);
  }

  const histories = new Map<string, PlayerStateHistoryRow[]>();
  for (const row of (data ?? []) as PlayerStateHistoryQueryRow[]) {
    const player = firstRelation(row.players);
    const tournament = firstRelation(row.tournaments);
    if (!player?.topdeck_id || !tournament?.state || !tournament.start_date) continue;
    const rows = histories.get(player.topdeck_id) ?? [];
    rows.push({
      state: tournament.state,
      city: tournament.city,
      start_date: tournament.start_date,
      player_count: tournament.player_count,
    });
    histories.set(player.topdeck_id, rows);
  }

  const predictions = new Map<string, string>();
  for (const [topdeckId, rows] of histories.entries()) {
    const prediction = predictNextState(rows);
    if (prediction) {
      predictions.set(topdeckId, prediction.state);
    }
  }
  return predictions;
}

async function fetchBestEloRows(topdeckIds: string[]): Promise<EloRow[]> {
  if (topdeckIds.length === 0) return [];

  const [{ data, error }, predictedRegions] = await Promise.all([
    supabase
      .from("regional_elo_leaderboard")
      .select("topdeck_id, player_name, rating, games_played, region_key, rank")
      .in("topdeck_id", topdeckIds)
      .eq("region_type", "global")
      .eq("region_key", "ALL"),
    fetchPredictedRegions(topdeckIds),
  ]);

  if (error) {
    throw new Error(`Error fetching Elo rows: ${error.message}`);
  }

  return ((data ?? []) as RegionalLeaderboardQueryRow[])
    .map((row) => ({
      topdeck_id: row.topdeck_id,
      player_name: row.player_name,
      rating: row.rating,
      games_played: row.games_played,
      region_key: row.topdeck_id ? predictedRegions.get(row.topdeck_id) ?? row.region_key : row.region_key,
    }))
    .sort((a, b) => b.rating - a.rating);
}

type TournamentAnalysis = {
  tournament: {
    name: string;
    game: string;
    format: string;
    startDate: string | number;
  };
  standings: TournamentStanding[];
  profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] };
  eloRows: EloRow[];
  hasRounds: boolean;
};

const getCachedTournamentAnalysis = unstable_cache(
  async (slug: string, lookbackMonths: number): Promise<TournamentAnalysis> => {
    const response = await fetchTournamentBySlug(slug);
    const standings = (response.standings ?? []) as TournamentStanding[];
    const topdeckIds = standings.map((row) => row.id).filter(Boolean);
    const startTimestamp = readStartTimestamp(response.data.startDate);
    const now = Date.now();
    const anchorToStartDate = Boolean(startTimestamp && now >= startTimestamp);
    const anchorTimestamp = anchorToStartDate && startTimestamp ? startTimestamp : now;
    const referenceDate = new Date(anchorTimestamp);
    const lookbackStart = lookbackStartDate(lookbackMonths, referenceDate);
    const fallbackLookbackStart = lookbackStartDate(COMMANDER_FALLBACK_LOOKBACK_MONTHS, referenceDate);
    const lookbackEnd = anchorToStartDate ? referenceDate.toISOString().slice(0, 10) : undefined;
    const [primaryUsageRows, decklistRows, eloRows] = await Promise.all([
      getCommanderUsageRows(topdeckIds, lookbackStart, lookbackEnd),
      getCommanderDecklistRows(topdeckIds, lookbackEnd),
      fetchBestEloRows(topdeckIds),
    ]);
    const twelveMonthEntryCounts = new Map<string, number>();
    for (const row of primaryUsageRows) {
      if (!row.topdeck_id || !row.commander_name) continue;
      twelveMonthEntryCounts.set(row.topdeck_id, (twelveMonthEntryCounts.get(row.topdeck_id) ?? 0) + 1);
    }
    const sparseTopdeckIds = topdeckIds.filter((topdeckId) => (twelveMonthEntryCounts.get(topdeckId) ?? 0) < 2);
    const fallbackUsageRows = sparseTopdeckIds.length
      ? await getCommanderUsageRows(sparseTopdeckIds, fallbackLookbackStart, lookbackStart)
      : [];
    for (const row of fallbackUsageRows) {
      if (!row.topdeck_id || !row.commander_name) continue;
      twelveMonthEntryCounts.set(row.topdeck_id, (twelveMonthEntryCounts.get(row.topdeck_id) ?? 0) + 1);
    }
    const noTwelveMonthHistoryTopdeckIds = topdeckIds.filter(
      (topdeckId) => (twelveMonthEntryCounts.get(topdeckId) ?? 0) === 0
    );
    const lastKnownFallbackRows = noTwelveMonthHistoryTopdeckIds.length
      ? await getCommanderUsageRows(noTwelveMonthHistoryTopdeckIds, "1900-01-01", fallbackLookbackStart)
      : [];
    const usageRows = selectCommanderForecastRows(
      topdeckIds,
      [...primaryUsageRows, ...fallbackUsageRows, ...lastKnownFallbackRows],
      referenceDate
    );
    const profiles = buildProfiles(topdeckIds, usageRows, 3, referenceDate.toISOString());

    return {
      tournament: response.data,
      standings,
      profiles: attachLatestDecklistUrls(profiles, decklistRows),
      eloRows,
      hasRounds: (response.rounds ?? []).length > 0,
    };
  },
  ["tournament-likelihood-analysis-v21"],
  { revalidate: 60 * 15 }
);

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
  let errorMessage: string | null = null;

  if (slug) {
    try {
      const analysis = await getCachedTournamentAnalysis(slug, lookbackMonths);
      tournament = analysis.tournament;
      standings = analysis.standings;
      profiles = analysis.profiles;
      eloRows = analysis.eloRows;
      hasRounds = analysis.hasRounds;
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  const playersWithData = profiles.players.filter((player) => player.totalEntries > 0).length;
  const tournamentHasStarted = tournament ? hasTournamentStarted(tournament.startDate) : false;
  const hasTournamentResults = tournamentHasStarted && hasRounds;
  const lookbackStartTimestamp = tournamentHasStarted && tournament
    ? readStartTimestamp(tournament.startDate)
    : null;
  const lookbackStart = lookbackStartDate(
    lookbackMonths,
    lookbackStartTimestamp ? new Date(lookbackStartTimestamp) : new Date()
  );

  const weightedMeta = new Map<string, number>();
  for (const player of profiles.players) {
    for (const commander of player.commanders) {
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
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers)
    .slice(0, 15);

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
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers)
    .slice(0, 15);

  const fieldShareRows = hasTournamentResults ? actualMetaRows : weightedMetaRows;
  const topCommander = fieldShareRows[0];
  const topFiveCombinedShare = fieldShareRows
    .slice(0, 5)
    .reduce((sum, row) => sum + row.fieldShare, 0);

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
            </nav>
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
                  <p className="mt-2 text-lg font-semibold text-foreground">{tournament.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {tournament.format} | {formatStartTime(tournament.startDate)}
                  </p>
                </div>
                <div className="rounded-md border border-border/60 bg-muted/20 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Attendees</p>
                  <p className="mt-2 text-lg font-semibold text-foreground">{standings.length}</p>
                  <p className="mt-1 text-sm text-muted-foreground">Players found from tournament standings</p>
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
                    {hasTournamentResults ? "Most Played Deck" : "Most Likely Deck"}
                  </p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {topCommander ? `${topCommander.commander} (${formatPercent(topCommander.fieldShare)})` : "No consensus yet"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Top 5 commanders represent {formatPercent(topFiveCombinedShare)} of{" "}
                    {hasTournamentResults ? "submitted decklists" : "known field history"}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel mt-6">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  {hasTournamentResults ? "Field Share" : "Expected Field Share (Player-Weighted)"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 text-sm text-muted-foreground">
                  {hasTournamentResults ? (
                    "Actual submitted commander choices from this tournament."
                  ) : (
                    "This estimate weights each player by how concentrated their recent commander usage is."
                  )}
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {fieldShareRows.map((row) => (
                    <div key={row.commander} className="flex items-center justify-between text-sm">
                      <span className="text-foreground">{row.commander}</span>
                      <span className="text-primary">
                        {formatPercent(row.fieldShare)} ·{" "}
                        {hasTournamentResults ? row.expectedPlayers : row.expectedPlayers.toFixed(1)} players
                      </span>
                    </div>
                  ))}
                  {!fieldShareRows.length && (
                    <div className="text-sm text-muted-foreground">
                      {hasTournamentResults
                        ? "No submitted decklists found for the players in this event."
                        : "No known commander history for the players in this event."}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <TournamentAnalysisTables
              eloAttendees={allTopEloAttendees}
              showActualDecks={hasTournamentResults}
              showTournamentRecord={tournamentHasStarted}
              profiles={profiles.players}
              standings={standings}
            />
          </>
        )}
      </main>
    </div>
  );
}
