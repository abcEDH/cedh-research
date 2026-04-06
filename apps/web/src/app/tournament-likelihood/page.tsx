import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { extractTournamentSlug, fetchTournamentBySlug } from "@/lib/topdeck";
import Link from "next/link";

export const dynamic = "force-dynamic";
const DEFAULT_LOOKBACK_MONTHS = 6;

type TournamentStanding = {
  name: string;
  id: string;
  username?: string | null;
  standing: number;
  points: number;
  winRate: number;
  opponentWinRate: number;
};

type EloRow = {
  topdeck_id: string | null;
  player_name: string;
  rating: number;
  games_played: number;
  region_key: string;
};

type PlayerEloQueryRow = {
  topdeck_id: string;
  name: string;
  regional_elo_ratings:
    | Array<{
        region_key: string;
        rating: number;
        games_played: number;
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

function formatDate(value: string | null | undefined) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

async function fetchBestEloRows(topdeckIds: string[]): Promise<EloRow[]> {
  if (topdeckIds.length === 0) return [];

  const { data, error } = await supabase
    .from("players")
    .select("topdeck_id, name, regional_elo_ratings(region_key, rating, games_played)")
    .in("topdeck_id", topdeckIds);

  if (error) {
    throw new Error(`Error fetching Elo rows: ${error.message}`);
  }

  return ((data ?? []) as PlayerEloQueryRow[])
    .map((player) => {
      const bestRegion = (player.regional_elo_ratings ?? []).reduce<
        | {
            region_key: string;
            rating: number;
            games_played: number;
          }
        | undefined
      >((best, row) => {
        if (!best || row.rating > best.rating) return row;
        return best;
      }, undefined);

      if (!bestRegion) return null;

      return {
        topdeck_id: player.topdeck_id,
        player_name: player.name,
        rating: bestRegion.rating,
        games_played: bestRegion.games_played,
        region_key: bestRegion.region_key,
      };
    })
    .filter((row): row is EloRow => Boolean(row))
    .sort((a, b) => b.rating - a.rating);
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
  const lookbackStart = lookbackStartDate(lookbackMonths);

  let tournament:
    | {
        name: string;
        game: string;
        format: string;
        startDate: string;
      }
    | null = null;
  let standings: TournamentStanding[] = [];
  let profiles: { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } = {
    players: [],
    metaShare: [],
  };
  let eloRows: EloRow[] = [];
  let errorMessage: string | null = null;

  if (slug) {
    try {
      const response = await fetchTournamentBySlug(slug);
      tournament = response.data;
      standings = (response.standings ?? []) as TournamentStanding[];
      const topdeckIds = standings.map((row) => row.id).filter(Boolean);
      const [usageRows, eloResult] = await Promise.all([
        getCommanderUsageRows(topdeckIds, lookbackStart),
        fetchBestEloRows(topdeckIds),
      ]);
      profiles = buildProfiles(topdeckIds, usageRows, 3);
      eloRows = eloResult;
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  const playersWithData = profiles.players.filter((player) => player.totalEntries > 0).length;
  const topDeckShares = profiles.players
    .filter((player) => player.commanders.length > 0)
    .map((player) => player.commanders[0]?.predictionShare ?? 0);
  const avgTopDeckShare = topDeckShares.length
    ? topDeckShares.reduce((sum, share) => sum + share, 0) / topDeckShares.length
    : 0;

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
  const topCommander = weightedMetaRows[0];
  const topFiveCombinedShare = weightedMetaRows
    .slice(0, 5)
    .reduce((sum, row) => sum + row.fieldShare, 0);

  const profileByPlayer = new Map(profiles.players.map((player) => [player.topdeckId, player]));
  const standingByPlayer = new Map(standings.map((player) => [player.id, player]));
  const topEloAttendees = eloRows
    .map((row) => ({
      ...row,
      standing: row.topdeck_id ? standingByPlayer.get(row.topdeck_id) : undefined,
      profile: row.topdeck_id ? profileByPlayer.get(row.topdeck_id) : undefined,
    }))
    .slice(0, 12);

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
              A fixed {lookbackMonths}-month window is used to balance recency against enough sample size.
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
                    {tournament.format} · {formatDate(tournament.startDate)}
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
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Most Likely Deck</p>
                  <p className="mt-2 text-lg font-semibold text-foreground">
                    {topCommander ? `${topCommander.commander} (${formatPercent(topCommander.fieldShare)})` : "No consensus yet"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Top 5 commanders represent {formatPercent(topFiveCombinedShare)} of known field history
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel mt-6">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Expected Field Share (Player-Weighted)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 text-sm text-muted-foreground">
                  This estimate weights each player by how concentrated their recent commander usage is.
                  Average top-deck concentration across attendees with data:{" "}
                  <span className="font-medium text-foreground">{formatPercent(avgTopDeckShare)}</span>.
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {weightedMetaRows.map((row) => (
                    <div key={row.commander} className="flex items-center justify-between text-sm">
                      <span className="text-foreground">{row.commander}</span>
                      <span className="text-primary">
                        {formatPercent(row.fieldShare)} · {row.expectedPlayers.toFixed(1)} players
                      </span>
                    </div>
                  ))}
                  {!weightedMetaRows.length && (
                    <div className="text-sm text-muted-foreground">
                      No known commander history for the players in this event.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel mt-6">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
                  Top Elo Attendees
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4 text-sm text-muted-foreground">
                  Highest-rated players in the field using the regional leaderboard&apos;s all-games Elo,
                  paired with the deck forecast from recent commander history.
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.3em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-3">Player</th>
                        <th className="px-2 py-3">Elo</th>
                        <th className="px-2 py-3">Home Region</th>
                        <th className="px-2 py-3">Most Likely Bring</th>
                        <th className="px-2 py-3">Alternatives</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topEloAttendees.map((row) => {
                        const topdeckHref = buildTopdeckProfileHref(row.topdeck_id);
                        const primary = row.profile?.commanders[0];
                        const alternatives = row.profile?.commanders.slice(1, 3) ?? [];
                        return (
                          <tr key={row.topdeck_id ?? row.player_name} className="border-t border-border/60">
                            <td className="px-2 py-4">
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
                              <div className="text-xs text-muted-foreground">
                                {row.standing ? `Tournament standing #${row.standing.standing}` : "Attendee"}
                              </div>
                            </td>
                            <td className="px-2 py-4 font-semibold text-primary">{Math.round(row.rating)}</td>
                            <td className="px-2 py-4 text-muted-foreground">{row.region_key}</td>
                            <td className="px-2 py-4">
                              {primary ? (
                                <div>
                                  <div className="font-medium text-foreground">{primary.commander}</div>
                                  <div className="text-xs text-muted-foreground">
                                    Forecast confidence {formatPercent(primary.predictionShare)} · {primary.entries} recent entries
                                  </div>
                                </div>
                              ) : (
                                <span className="text-xs text-muted-foreground">No recent deck data</span>
                              )}
                            </td>
                            <td className="px-2 py-4">
                              <div className="flex flex-wrap gap-2">
                                {alternatives.length ? (
                                  alternatives.map((commander) => (
                                    <span key={`${row.topdeck_id}-${commander.commander}`} className="knd-chip">
                                      {commander.commander} · {formatPercent(commander.predictionShare)}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-muted-foreground">No strong alternatives</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                      {topEloAttendees.length === 0 && (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-sm text-muted-foreground">
                            No Elo rows matched the current attendee list.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
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
                        <th className="px-2 py-3">Standing</th>
                        <th className="px-2 py-3">Player</th>
                        <th className="px-2 py-3">Tournament Record</th>
                        <th className="px-2 py-3">Likely Decks</th>
                      </tr>
                    </thead>
                    <tbody>
                      {standings.map((entry) => {
                        const profile = profileByPlayer.get(entry.id);
                        const profileHref = buildTopdeckProfileHref(entry.username || entry.id);
                        return (
                          <tr key={`${entry.id}-${entry.standing}`} className="border-t border-border/60">
                            <td className="px-2 py-4 text-muted-foreground">#{entry.standing}</td>
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
                              <div className="text-xs text-muted-foreground">{entry.username || entry.id}</div>
                            </td>
                            <td className="px-2 py-4 text-muted-foreground">
                              {entry.points} pts · {Math.round((entry.winRate || 0) * 100)}% WR
                            </td>
                            <td className="px-2 py-4">
                              <div className="flex flex-wrap gap-2">
                                {profile?.commanders?.length ? (
                                  profile.commanders.map((commander) => (
                                    <span key={`${entry.id}-${commander.commander}`} className="knd-chip">
                                      {commander.commander} · {formatPercent(commander.predictionShare)} ({commander.entries})
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
          </>
        )}
      </main>
    </div>
  );
}
