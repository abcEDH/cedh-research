import Link from "next/link";
import { unstable_cache } from "next/cache";
import { withTiming } from "@/lib/performance";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchCanonicalPlayerLogs,
  fetchPlayer,
  type PlayerRow,
} from "../../player-log-data";
import { buildPlayerVersusHref } from "../../player-routes";
import { filterPlayerLogs } from "../../player-stats";

const PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS = 60 * 60 * 24; // 24 hours

const fetchCachedCanonicalPlayerLogs = unstable_cache(
  async (playerId: string) =>
    withTiming("regional-player:canonical-logs", () => fetchCanonicalPlayerLogs(playerId)),
  ["regional-player-canonical-logs-v1"],
  { revalidate: PLAYER_PROFILE_CACHE_REVALIDATE_SECONDS }
);

function formatShortDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatRecord(wins: number, losses: number, draws: number) {
  return `${wins}-${losses}-${draws}`;
}

function participantTone(role: "subject" | "opponent" | "other") {
  if (role === "subject") return "font-semibold text-foreground";
  if (role === "opponent") return "font-semibold text-foreground";
  return "text-foreground";
}

function participantRowClass(result: string) {
  if (result === "win") {
    return "border-t border-fuchsia-500/45 bg-fuchsia-500/12";
  }
  return "border-t border-border/60";
}

function gameSummaryClass(
  gameResultLabel: string,
  player: PlayerRow,
  opponent: PlayerRow
) {
  if (gameResultLabel === `${player.name} won`) {
    return "rounded-xl border border-emerald-500/40 bg-emerald-500/10";
  }
  if (gameResultLabel === `${opponent.name} won`) {
    return "rounded-xl border border-sky-500/40 bg-sky-500/10";
  }
  if (gameResultLabel === "Draw") {
    return "rounded-xl border border-slate-400/40 bg-slate-400/10";
  }
  return "rounded-xl border border-amber-500/40 bg-amber-500/10";
}

function summaryPillClass() {
  return "rounded-full border border-border/60 bg-background/40 px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-muted-foreground";
}

function resultBadgeClass(
  gameResultLabel: string,
  player: PlayerRow,
  opponent: PlayerRow
) {
  const base = "rounded-full px-3 py-1 text-[11px] font-medium uppercase tracking-[0.14em]";
  if (gameResultLabel === `${player.name} won`) {
    return `${base} border border-emerald-500/40 bg-emerald-500/15 text-emerald-100`;
  }
  if (gameResultLabel === `${opponent.name} won`) {
    return `${base} border border-sky-500/40 bg-sky-500/15 text-sky-100`;
  }
  if (gameResultLabel === "Draw") {
    return `${base} border border-slate-400/40 bg-slate-400/15 text-slate-100`;
  }
  return `${base} border border-amber-500/40 bg-amber-500/15 text-amber-100`;
}

function describeGameResult(
  player: PlayerRow,
  podRows: Array<{
    seat: number;
    playerName: string;
    topdeckId: string | null;
    commanderName: string | null;
    result: string;
    role: "subject" | "opponent" | "other";
  }>
) {
  const winners = podRows.filter((podPlayer) => podPlayer.result === "win");
  if (winners.length === 0) return "Draw";
  if (winners.length === 1) {
    return `${winners[0].playerName} won`;
  }
  if (winners.some((podPlayer) => podPlayer.topdeckId === player.topdeck_id)) {
    return `${player.name} won`;
  }
  return `${winners[0].playerName} won`;
}

function formatPlayerSeatCommanderLabel(
  playerName: string,
  seat: number | null | undefined,
  commanderName: string | null | undefined
) {
  return `${playerName}: Seat ${seat ?? "?"}, ${commanderName ?? "Unknown Commander"}`;
}

function buildPodRows(player: PlayerRow, opponent: PlayerRow, log: Awaited<ReturnType<typeof fetchCanonicalPlayerLogs>>[number]) {
  return [
    {
      seat: log.seat,
      playerName: player.name,
      topdeckId: player.topdeck_id,
      commanderName: log.commanderName,
      result: log.result,
      role: "subject" as const,
    },
    ...log.opponents.map((podPlayer) => ({
      seat: podPlayer.seat,
      playerName: podPlayer.playerName,
      topdeckId: podPlayer.topdeckId,
      commanderName: podPlayer.commanderName,
      result: podPlayer.result,
      role: podPlayer.topdeckId === opponent.topdeck_id ? ("opponent" as const) : ("other" as const),
    })),
  ].sort((left, right) => left.seat - right.seat);
}

function countResults(results: Array<string | null | undefined>) {
  return results.reduce(
    (totals, result) => {
      if (result === "win") {
        totals.wins += 1;
      } else if (result === "draw") {
        totals.draws += 1;
      } else if (result === "loss") {
        totals.losses += 1;
      }
      return totals;
    },
    { wins: 0, losses: 0, draws: 0 }
  );
}

function buildCommanderStats(
  rows: Array<{ commanderName: string | null | undefined; result: string | null | undefined }>
) {
  const stats = new Map<
    string,
    { commanderName: string; games: number; wins: number; losses: number; draws: number }
  >();

  for (const row of rows) {
    const commanderName = row.commanderName ?? "Unknown Commander";
    const current = stats.get(commanderName) ?? {
      commanderName,
      games: 0,
      wins: 0,
      losses: 0,
      draws: 0,
    };
    current.games += 1;
    if (row.result === "win") {
      current.wins += 1;
    } else if (row.result === "loss") {
      current.losses += 1;
    } else if (row.result === "draw") {
      current.draws += 1;
    }
    stats.set(commanderName, current);
  }

  return Array.from(stats.values()).sort((left, right) => {
    if (right.games !== left.games) return right.games - left.games;
    if (right.wins !== left.wins) return right.wins - left.wins;
    return left.commanderName.localeCompare(right.commanderName);
  });
}

export default async function RegionalPlayerVsPage({
  params,
  searchParams,
}: {
  params:
    | Promise<{ topdeckId: string; opponentTopdeckId: string }>
    | { topdeckId: string; opponentTopdeckId: string };
  searchParams?:
    | Promise<Record<string, string | string[] | undefined>>
    | Record<string, string | string[] | undefined>;
}) {
  const resolvedParams = await Promise.resolve(params);
  const { topdeckId, opponentTopdeckId } = resolvedParams;

  const [player, opponent] = await Promise.all([fetchPlayer(topdeckId), fetchPlayer(opponentTopdeckId)]);
  if (!player || !opponent) {
    return (
      <main className="container mx-auto px-4 py-10">
        <p className="text-sm text-muted-foreground">Player matchup not found.</p>
      </main>
    );
  }

  const resolvedSearchParams = await Promise.resolve(searchParams);
  const rawEloOnly = resolvedSearchParams?.eloOnly;
  const eloOnly = Array.isArray(rawEloOnly) ? rawEloOnly[0] === "true" : rawEloOnly === "true";
  const playerLogs = filterPlayerLogs(await fetchCachedCanonicalPlayerLogs(player.id), eloOnly);
  const sharedLogs = playerLogs.filter((log) =>
    log.opponents.some((podPlayer) => podPlayer.topdeckId === opponentTopdeckId)
  );

  const playerRecord = countResults(sharedLogs.map((log) => log.result));
  const opponentRecord = countResults(
    sharedLogs.map(
      (log) => log.opponents.find((podPlayer) => podPlayer.topdeckId === opponentTopdeckId)?.result
    )
  );
  const playerCommanderStats = buildCommanderStats(
    sharedLogs.map((log) => ({
      commanderName: log.commanderName,
      result: log.result,
    }))
  );
  const opponentCommanderStats = buildCommanderStats(
    sharedLogs.map((log) => {
      const opponentRow = log.opponents.find((podPlayer) => podPlayer.topdeckId === opponentTopdeckId);
      return {
        commanderName: opponentRow?.commanderName,
        result: opponentRow?.result,
      };
    })
  );
  const latestSharedDate = sharedLogs[0]?.startDate ?? null;
  const earliestSharedDate = sharedLogs[sharedLogs.length - 1]?.startDate ?? null;
  const toggleHref = eloOnly
    ? buildPlayerVersusHref(topdeckId, opponentTopdeckId)
    : `${buildPlayerVersusHref(topdeckId, opponentTopdeckId)}?eloOnly=true`;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-20 pt-10">
        <div className="space-y-8">
          <div className="space-y-3">
            <Link href={`/regional-elo/player/${topdeckId}`} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to player profile
            </Link>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold leading-tight text-foreground sm:text-3xl md:text-4xl">
                  {player.name} vs {opponent.name}
                </h1>
                <p className="mt-2 max-w-3xl text-sm text-muted-foreground">
                  Shared game history, mirrored head-to-head record, and full pod context.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-sm">
                <Link
                  href={`/regional-elo/player/${topdeckId}`}
                  className="w-full rounded-md border border-border/70 px-3 py-2 text-center text-foreground hover:border-primary/40 hover:text-primary sm:w-auto"
                >
                  {player.name} profile
                </Link>
                <Link
                  href={`/regional-elo/player/${opponentTopdeckId}`}
                  className="w-full rounded-md border border-border/70 px-3 py-2 text-center text-foreground hover:border-primary/40 hover:text-primary sm:w-auto"
                >
                  {opponent.name} profile
                </Link>
              </div>
            </div>
          </div>

          <Card className="knd-panel">
            <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
              <div>
                <div className="text-sm font-medium text-foreground">Game filter</div>
                <p className="text-xs text-muted-foreground">
                  Shared W-L-D stats can be limited to Elo-worthy events with 30+ players; Elo
                  rankings are unchanged.
                </p>
              </div>
              <div className="flex min-h-11 items-center gap-3">
                <span className="text-sm text-foreground">Show 30+ player games only</span>
                <Link
                  href={toggleHref}
                  role="switch"
                  aria-checked={eloOnly}
                  aria-label="Show 30+ player games only"
                  className="inline-flex min-h-11 min-w-11 items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
                >
                  <span
                    aria-hidden="true"
                    className={`relative block h-6 w-11 rounded-full transition-colors ${
                      eloOnly ? "bg-primary" : "bg-muted-foreground/40"
                    }`}
                  >
                    <span
                      className={`absolute top-1 h-4 w-4 rounded-full bg-background shadow-sm transition-transform ${
                        eloOnly ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </span>
                </Link>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <Card className="knd-panel xl:col-span-2">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  {player.name} Record
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {formatRecord(playerRecord.wins, playerRecord.losses, playerRecord.draws)}
                </div>
                <div className="text-sm text-muted-foreground">
                  Perspective:{" "}
                  <Link href={buildPlayerVersusHref(topdeckId, opponentTopdeckId)} className="hover:text-primary">
                    {player.name}
                  </Link>
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel xl:col-span-2">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  {opponent.name} Record
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-semibold text-foreground">
                  {formatRecord(opponentRecord.wins, opponentRecord.losses, opponentRecord.draws)}
                </div>
                <div className="text-sm text-muted-foreground">
                  Perspective:{" "}
                  <Link href={buildPlayerVersusHref(opponentTopdeckId, topdeckId)} className="hover:text-primary">
                    {opponent.name}
                  </Link>
                </div>
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Shared Games
                </CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-semibold text-foreground">
                {sharedLogs.length}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  Latest Meeting
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm font-medium text-foreground">
                {formatShortDate(latestSharedDate)}
              </CardContent>
            </Card>
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  First Meeting
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm font-medium text-foreground">
                {formatShortDate(earliestSharedDate)}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  {player.name} Commander Stats
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="max-h-80 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-3">Commander</th>
                        <th className="px-2 py-3 text-right">Games</th>
                        <th className="px-2 py-3 text-right">W-L-D</th>
                      </tr>
                    </thead>
                    <tbody>
                      {playerCommanderStats.map((row) => (
                        <tr key={`${player.topdeck_id}:${row.commanderName}`} className="border-t border-border/60">
                          <td className="px-2 py-3 font-medium text-foreground">{row.commanderName}</td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">{row.games}</td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>

            <Card className="knd-panel">
              <CardHeader>
                <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                  {opponent.name} Commander Stats
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="max-h-80 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <tr>
                        <th className="px-2 py-3">Commander</th>
                        <th className="px-2 py-3 text-right">Games</th>
                        <th className="px-2 py-3 text-right">W-L-D</th>
                      </tr>
                    </thead>
                    <tbody>
                      {opponentCommanderStats.map((row) => (
                        <tr key={`${opponent.topdeck_id}:${row.commanderName}`} className="border-t border-border/60">
                          <td className="px-2 py-3 font-medium text-foreground">{row.commanderName}</td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">{row.games}</td>
                          <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                            {row.wins}-{row.losses}-{row.draws}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="knd-panel">
            <CardHeader>
              <CardTitle className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
                Chronological Game History
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Sorted newest first. Expand a game to see the full pod and winner highlight.
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              {sharedLogs.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No shared games found between {player.name} and {opponent.name}.
                </p>
              ) : (
                sharedLogs.map((log) => {
                  const podRows = buildPodRows(player, opponent, log);
                  const gameResultLabel = describeGameResult(player, podRows);
                  const opponentRow =
                    podRows.find((podPlayer) => podPlayer.topdeckId === opponent.topdeck_id) ?? null;
                  return (
                    <details key={log.gameId} className={gameSummaryClass(gameResultLabel, player, opponent)}>
                      <summary className="cursor-pointer list-none px-4 py-4">
                        <div className="space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="min-w-0 flex-1">
                              <div className="truncate text-sm font-semibold text-foreground sm:text-base">
                                {log.tournamentName}
                              </div>
                            </div>
                            <div className={resultBadgeClass(gameResultLabel, player, opponent)}>
                              {gameResultLabel}
                            </div>
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className={summaryPillClass()}>{formatShortDate(log.startDate)}</span>
                              <span className={summaryPillClass()}>{log.roundLabel}</span>
                              <span className={summaryPillClass()}>{log.tableLabel}</span>
                              {log.state ? (
                                <span className={summaryPillClass()}>{log.state.toUpperCase()}</span>
                              ) : null}
                              <span className="rounded-full border border-border/60 bg-background/30 px-2.5 py-1 text-[11px] text-muted-foreground">
                                {formatPlayerSeatCommanderLabel(player.name, log.seat, log.commanderName)}
                              </span>
                              <span className="rounded-full border border-border/60 bg-background/30 px-2.5 py-1 text-[11px] text-muted-foreground">
                                {formatPlayerSeatCommanderLabel(
                                  opponent.name,
                                  opponentRow?.seat,
                                  opponentRow?.commanderName
                                )}
                              </span>
                            </div>
                          </div>
                        </div>
                      </summary>
                      <div className="border-t border-border/60 px-4 py-4">
                        <div className="overflow-auto">
                          <table className="w-full text-sm">
                            <thead className="text-left text-xs uppercase tracking-[0.2em] text-muted-foreground">
                              <tr>
                                <th className="px-2 py-3">Seat</th>
                                <th className="px-2 py-3">Player</th>
                                <th className="px-2 py-3">Commander</th>
                                <th className="px-2 py-3 text-right">Result</th>
                              </tr>
                            </thead>
                            <tbody>
                              {podRows.map((podPlayer) => (
                                <tr
                                  key={`${log.gameId}:${podPlayer.seat}:${podPlayer.playerName}`}
                                  className={participantRowClass(podPlayer.result)}
                                >
                                  <td className="px-2 py-3 font-mono text-muted-foreground">{podPlayer.seat}</td>
                                  <td className="px-2 py-3">
                                    {podPlayer.topdeckId ? (
                                      <Link
                                        href={`/regional-elo/player/${podPlayer.topdeckId}`}
                                        className={`${participantTone(podPlayer.role)} hover:text-primary`}
                                      >
                                        {podPlayer.playerName}
                                      </Link>
                                    ) : (
                                      <span className={participantTone(podPlayer.role)}>{podPlayer.playerName}</span>
                                    )}
                                  </td>
                                  <td className="px-2 py-3 text-muted-foreground">
                                    {podPlayer.commanderName ?? "Unknown Commander"}
                                  </td>
                                  <td className="px-2 py-3 text-right font-mono text-muted-foreground">
                                    {podPlayer.result === "win" ? "WINNER" : podPlayer.result.toUpperCase()}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </details>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
