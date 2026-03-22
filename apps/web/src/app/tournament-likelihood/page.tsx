import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildProfiles, getCommanderUsageRows, lookbackStartDate } from "@/lib/meta-prep";
import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { extractTournamentSlug, fetchTournamentBySlug } from "@/lib/topdeck";
import Link from "next/link";

export const dynamic = "force-dynamic";

type TournamentStanding = {
  name: string;
  id: string;
  username?: string | null;
  standing: number;
  points: number;
  winRate: number;
  opponentWinRate: number;
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

export default async function TournamentLikelihoodPage({
  searchParams,
}: {
  searchParams?:
    | Promise<{ tournament?: string; months?: string }>
    | { tournament?: string; months?: string };
}) {
  const resolvedSearchParams = await Promise.resolve(searchParams);
  const tournamentInput = readStringParam(resolvedSearchParams, "tournament").trim();
  const monthsInput = readStringParam(resolvedSearchParams, "months").trim();
  const slug = extractTournamentSlug(tournamentInput);
  const months = Number(monthsInput || "12");
  const lookbackMonths = Number.isFinite(months) && months > 0 ? months : 12;
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
  let errorMessage: string | null = null;

  if (slug) {
    try {
      const response = await fetchTournamentBySlug(slug);
      tournament = response.data;
      standings = (response.standings ?? []) as TournamentStanding[];
      const topdeckIds = standings.map((row) => row.id).filter(Boolean);
      const usageRows = await getCommanderUsageRows(topdeckIds, lookbackStart);
      profiles = buildProfiles(topdeckIds, usageRows, 3);
    } catch (error) {
      errorMessage = (error as Error).message;
    }
  }

  const playersWithData = profiles.players.filter((player) => player.totalEntries > 0).length;
  const topCommander = profiles.metaShare[0];
  const topFiveCombinedShare = profiles.metaShare
    .slice(0, 5)
    .reduce((sum, row) => sum + row.share, 0);
  const topDeckShares = profiles.players
    .filter((player) => player.commanders.length > 0)
    .map((player) => player.commanders[0]?.share ?? 0);
  const avgTopDeckShare = topDeckShares.length
    ? topDeckShares.reduce((sum, share) => sum + share, 0) / topDeckShares.length
    : 0;

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
      fieldShare: standings.length ? expectedPlayers / standings.length : 0,
      expectedPlayers,
    }))
    .sort((a, b) => b.expectedPlayers - a.expectedPlayers)
    .slice(0, 15);

  const profileByPlayer = new Map(profiles.players.map((player) => [player.topdeckId, player]));

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
            <form className="grid gap-4 lg:grid-cols-[1fr_180px_auto]" method="get">
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
              <label className="flex flex-col gap-2 text-sm text-muted-foreground">
                Lookback window
                <select className="knd-input" defaultValue={String(lookbackMonths)} name="months">
                  <option value="3">Last 3 months</option>
                  <option value="6">Last 6 months</option>
                  <option value="12">Last 12 months</option>
                  <option value="18">Last 18 months</option>
                </select>
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
                    {topCommander ? `${topCommander.commander} (${formatPercent(topCommander.share)})` : "No consensus yet"}
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
                                      {commander.commander} · {formatPercent(commander.share)} ({commander.entries})
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
