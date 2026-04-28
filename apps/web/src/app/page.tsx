import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ColorBadge } from "@/components/ui/color-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CommanderRow, RisingCommanderRow } from "@/components/home/commander-row";
import { FeatureCard } from "@/components/home/feature-card";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import { isKnownCommanderName } from "@/lib/commander-utils";
import Link from "next/link";
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";
import { HomeSearchBar } from "@/components/home-search-bar";

// Force dynamic rendering - fetch fresh data on each request
export const dynamic = "force-dynamic";

interface TopCommander {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: number;
  conversion_rate_top_16: number;
  color_identity: string[] | null;
  /** Share of all `commander_stats` entries (32+ player events); set on home widgets only. */
  meta_share_pct?: number;
}

interface RisingCommander {
  commander_id: string;
  commander_name: string;
  entries_delta: number;
  meta_share_delta: number;
  recent_entries: number;
  prior_entries: number;
  total_entries: number;
  avg_win_rate: number;
  color_identity: string[] | null;
  /** Share of all `commander_stats` entries (32+ player events). */
  meta_share_pct?: number;
}

/** Sum of `total_entries` across `commander_stats` (equals all large-event tournament entries). */
async function sumMetaEntriesFromCommanderStats(): Promise<number> {
  try {
    const pageSize = 1000;
    let sum = 0;
    for (let offset = 0; ; offset += pageSize) {
      const { data, error } = await supabase
        .from("commander_stats")
        .select("total_entries")
        .range(offset, offset + pageSize - 1);
      if (error) {
        console.error("Meta entry total sum error:", error);
        return 0;
      }
      const rows = data ?? [];
      if (rows.length === 0) break;
      for (const row of rows) {
        sum += Number(row.total_entries) || 0;
      }
      if (rows.length < pageSize) break;
    }
    return sum;
  } catch (e) {
    console.error("Meta entry total sum unexpected error:", e);
    return 0;
  }
}

function addDaysIso(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00.000Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Orders commanders by the largest gain in weekly tournament entries: sums the two most recent
 * ISO weeks from `commander_weekly_trends` and subtracts the sum for the two weeks before that
 * (32+ player events; same filter as the materialized view).
 */
async function getTopRisingCommandersByTwoWeekTrend(): Promise<RisingCommander[]> {
  try {
    const { data: maxRows, error: maxErr } = await supabase
      .from("commander_weekly_trends")
      .select("week_start_date")
      .not("commander_name", "ilike", "unknown commander")
      .not("commander_name", "is", null)
      .neq("commander_name", "")
      .order("week_start_date", { ascending: false })
      .limit(1);

    if (maxErr || !maxRows?.[0]?.week_start_date) {
      if (maxErr) console.error("Rising commanders: max week query error:", maxErr);
      return [];
    }

    const latestWeek = maxRows[0].week_start_date as string;
    const windowStart = addDaysIso(latestWeek, -35);

    const { data: trendRows, error: trendErr } = await supabase
      .from("commander_weekly_trends")
      .select("commander_id, commander_name, week_start_date, entries")
      .not("commander_name", "ilike", "unknown commander")
      .not("commander_name", "is", null)
      .neq("commander_name", "")
      .gte("week_start_date", windowStart)
      .lte("week_start_date", latestWeek);

    if (trendErr || !trendRows?.length) {
      if (trendErr) console.error("Rising commanders: trends window query error:", trendErr);
      return [];
    }

    const weekSet = [...new Set(trendRows.map((r) => r.week_start_date as string))].sort((a, b) =>
      b.localeCompare(a)
    );

    if (weekSet.length < 2) return [];

    const recentWeekDates = weekSet.slice(0, 2);
    let priorWeekDates: string[];
    if (weekSet.length >= 4) {
      priorWeekDates = weekSet.slice(2, 4);
    } else if (weekSet.length === 3) {
      priorWeekDates = weekSet.slice(2, 3);
    } else {
      priorWeekDates = [];
    }

    const recentKey = new Set(recentWeekDates);
    const priorKey = new Set(priorWeekDates);

    let recentTotal = 0;
    let priorTotal = 0;
    const totals = new Map<string, { name: string; recent: number; prior: number }>();
    for (const row of trendRows) {
      const id = row.commander_id as string;
      const wk = row.week_start_date as string;
      const n = row.entries ?? 0;
      const cur = totals.get(id) ?? { name: row.commander_name as string, recent: 0, prior: 0 };
      if (recentKey.has(wk)) {
        cur.recent += n;
        recentTotal += n;
      }
      if (priorKey.has(wk)) {
        cur.prior += n;
        priorTotal += n;
      }
      totals.set(id, cur);
    }

    const scored = [...totals.entries()]
      .map(([commander_id, v]) => ({
        commander_id,
        commander_name: v.name,
        entries_delta: v.recent - v.prior,
        meta_share_delta: (v.recent / recentTotal) - (v.prior / priorTotal),
        recent_entries: v.recent,
        prior_entries: v.prior,
      }))
      .filter((x) => x.meta_share_delta > 0)
      .sort((a, b) => b.meta_share_delta - a.meta_share_delta)
      .slice(0, 3);

    if (scored.length === 0) return [];

    const { data: metaRows, error: metaErr } = await supabase
      .from("commander_stats")
      .select("commander_id, color_identity, avg_win_rate, total_entries")
      .in(
        "commander_id",
        scored.map((s) => s.commander_id)
      );

    if (metaErr) {
      console.error("Rising commanders: commander_stats enrich error:", metaErr);
    }

    const metaById = new Map((metaRows ?? []).map((m) => [m.commander_id as string, m]));

    return scored.map((s) => {
      const meta = metaById.get(s.commander_id);
      const wr = meta?.avg_win_rate;
      const avg_win_rate = typeof wr === "number" ? wr : Number(wr ?? 0);
      const te = meta?.total_entries;
      const total_entries = typeof te === "number" ? te : Number(te ?? 0);
      return {
        ...s,
        total_entries: Number.isFinite(total_entries) ? total_entries : 0,
        color_identity: (meta?.color_identity as string[] | null) ?? null,
        avg_win_rate: Number.isFinite(avg_win_rate) ? avg_win_rate : 0,
      };
    });
  } catch (e) {
    console.error("Rising commanders: unexpected error:", e);
    return [];
  }
}

async function getStats() {
  try {
    const [
      tournamentResult,
      commanderResult,
      topCommandersResult,
      topWinRateResult,
      topRisingCommanders,
      metaEntryTotal,
    ] = await Promise.all([
      supabase.from("tournaments").select("*", { count: "exact", head: true }),
      supabase.from("commanders").select("*", { count: "exact", head: true }),
      supabase
        .from("commander_stats")
        .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_16, color_identity")
        .gt("total_entries", 20)
        .not("commander_name", "ilike", "unknown commander")
        .not("commander_name", "is", null)
        .neq("commander_name", "")
        .order("total_entries", { ascending: false })
        .limit(21),
      supabase
        .from("commander_stats")
        .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_16, color_identity")
        .gt("total_entries", 30)
        .not("commander_name", "ilike", "unknown commander")
        .not("commander_name", "is", null)
        .neq("commander_name", "")
        .order("avg_win_rate", { ascending: false })
        .limit(10),
      getTopRisingCommandersByTwoWeekTrend(),
      sumMetaEntriesFromCommanderStats(),
    ]);

    if (tournamentResult.error) {
      console.error("Tournament query error:", tournamentResult.error);
    }
    if (commanderResult.error) {
      console.error("Commander query error:", commanderResult.error);
    }
    if (topCommandersResult.error) {
      console.error("Top commanders query error:", topCommandersResult.error);
    }

    let topPlayers: Awaited<ReturnType<typeof fetchChampionshipLeaderboard>> = [];
    try {
      topPlayers = (await fetchChampionshipLeaderboard()).sort((a, b) => a.rank - b.rank).slice(0, 12);
    } catch (error) {
      console.error("Top players query error:", error);
    }

    return {
      tournamentCount: tournamentResult.count ?? 0,
      commanderCount: commanderResult.count ?? 0,
      topCommanders: ((topCommandersResult.data ?? []) as TopCommander[]).filter((row) =>
        isKnownCommanderName(row.commander_name)
      ),
      topWinRate: ((topWinRateResult.data ?? []) as TopCommander[]).filter((row) =>
        isKnownCommanderName(row.commander_name)
      ),
      topRisingCommanders,
      metaEntryTotal,
      topPlayers,
    };
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return {
      tournamentCount: 0,
      commanderCount: 0,
      topCommanders: [],
      topWinRate: [],
      topRisingCommanders: [],
      metaEntryTotal: 0,
      topPlayers: [],
    };
  }
}

function metaSharePercent(totalEntries: number, metaEntryTotal: number): number | undefined {
  if (metaEntryTotal <= 0 || !Number.isFinite(totalEntries)) return undefined;
  return (100 * totalEntries) / metaEntryTotal;
}

export default async function Home() {
  const { topCommanders, topWinRate, topRisingCommanders, metaEntryTotal, topPlayers } = await getStats();
  const topThreePopular: TopCommander[] = topCommanders.slice(0, 3).map((c) => ({
    ...c,
    meta_share_pct: metaSharePercent(c.total_entries, metaEntryTotal),
  }));
  const topRisingWithMeta: RisingCommander[] = topRisingCommanders.map((c) => ({
    ...c,
    meta_share_pct: metaSharePercent(c.total_entries, metaEntryTotal),
  }));

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-foreground md:text-4xl">cEDH Analytics</h1>
            </div>
            <nav className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <Link className="transition hover:text-foreground" href="/commanders">
                Commanders
              </Link>
              <Link className="transition hover:text-foreground" href="/tournament-likelihood">
                Tournament Prep
              </Link>
              <Link className="transition hover:text-foreground" href="/regional-elo">
                Leaderboard
              </Link>
              <Link className="transition hover:text-foreground" href="/about">
                Methodology
              </Link>
              <a
                className="transition hover:text-foreground"
                href="https://github.com/victoremnm/cedh-research"
                rel="noreferrer"
                target="_blank"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>

        <section className="mt-16 flex flex-col items-center gap-8 py-8 text-center">
          <div className="space-y-3">
            <h2 className="text-3xl font-semibold leading-tight text-foreground md:text-4xl">
              Competitive Commander analytics
            </h2>
            <p className="text-base text-muted-foreground">
              Your finger on the pulse of the cEDH meta.
            </p>
          </div>
          <HomeSearchBar />
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="sm" variant="outline" className="border-border/70 bg-muted/30">
              <Link href="/commanders">Commanders</Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="border-border/70 bg-muted/30">
              <Link href="/regional-elo">Leaderboard</Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="border-border/70 bg-muted/30">
              <Link href="/about">Methodology</Link>
            </Button>
          </div>
        </section>

        {topThreePopular.length > 0 || topRisingWithMeta.length > 0 ? (
          <section className="mt-12 grid gap-6 lg:grid-cols-2">
            {topThreePopular.length > 0 ? (
              <Card data-testid="top-popular-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Top 3 most popular commanders</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Ranked by total entries in large events—same metric as the performance table below. Meta share is
                    each commander&apos;s percent of all entries in 32+ player events.
                  </p>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {topThreePopular.map((commander, index) => (
                    <CommanderRow
                      key={commander.commander_id}
                      commander={commander}
                      rank={index + 1}
                    />
                  ))}
                </CardContent>
              </Card>
            ) : null}
            {topRisingWithMeta.length > 0 ? (
              <Card data-testid="top-rising-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Biggest popularity gain (2 weeks)</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Extra tournament entries in the latest two ISO weeks vs the stretch before that (32+ player events).
                    Raw meta share is overall large-event share, not the 2-week slice.
                  </p>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {topRisingWithMeta.map((commander, index) => (
                    <RisingCommanderRow
                      key={commander.commander_id}
                      commander={commander}
                      rank={index + 1}
                    />
                  ))}
                </CardContent>
              </Card>
            ) : null}
          </section>
        ) : null}

        <section className="mt-12 grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Commander performance</CardTitle>
              <p className="text-sm text-muted-foreground">Sorted by total entries</p>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    <TableHead className="py-3">Rank</TableHead>
                    <TableHead className="py-3">Commander</TableHead>
                    <TableHead className="py-3">Entries</TableHead>
                    <TableHead className="py-3">Win rate</TableHead>
                    <TableHead className="py-3">Top Bracket%</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topCommanders.map((commander, index) => (
                    <TableRow key={commander.commander_id} className="border-border/60">
                      <TableCell className="font-mono text-xs text-muted-foreground">#{index + 1}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="flex gap-1">
                            {commander.color_identity?.filter(Boolean).map((color: string) => (
                              <ColorBadge key={color} color={color} />
                            ))}
                          </div>
                          <Link
                            className="max-w-[220px] truncate text-sm font-medium text-foreground hover:text-primary"
                            href={`/commanders/${commander.commander_id}`}
                          >
                            {normalizeDisplayString(commander.commander_name)}
                          </Link>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm text-primary">
                        {commander.total_entries}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {(commander.avg_win_rate * 100).toFixed(1)}%
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        {(commander.conversion_rate_top_16 * 100).toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">Highest win rate</CardTitle>
              <p className="text-sm text-muted-foreground">30+ entries minimum</p>
            </CardHeader>
            <CardContent className="space-y-3">
              {topWinRate.map((commander, index) => (
                <CommanderRow key={commander.commander_id} commander={commander} rank={index + 1} />
              ))}
              <Button asChild variant="ghost" className="w-full border border-border/70">
                <Link href="/commanders">View all commanders</Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        <section className="mt-12">
          <Card>
            <CardHeader className="knd-panel-header">
              <CardTitle className="text-lg">TopDeck Championship Snapshot</CardTitle>
              <p className="text-sm text-muted-foreground">Current TopDeck Championship Series top 100 leaders</p>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2">
                {topPlayers.map((player) => {
                  const href = buildTopdeckProfileHref(player.username || player.uid);
                  return (
                    <div
                      key={player.uid}
                      className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-3"
                    >
                      <div className="min-w-0">
                        <div className="text-xs text-muted-foreground">#{player.rank}</div>
                        {href ? (
                          <a
                            className="truncate text-sm font-medium text-foreground hover:text-primary"
                            href={href}
                            rel="noreferrer"
                            target="_blank"
                          >
                            {player.name}
                          </a>
                        ) : (
                          <div className="truncate text-sm font-medium text-foreground">{player.name}</div>
                        )}
                      </div>
                      <div className="font-mono text-sm text-primary">{player.points}</div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <FeatureCard
            href="/commanders"
            title="Commander Rankings"
            description="Sortable performance data for all commanders"
            color="hsl(var(--knd-cyan))"
          />
          <FeatureCard
            href="/trap-spice"
            title="Trap & Spice Cards"
            description="Find overrated and underrated cards"
            color="hsl(var(--knd-amber))"
          />
          <FeatureCard
            href="/tournament-likelihood"
            title="Tournament Prep"
            description="Estimate attendee commander likelihood and expected meta share"
            color="hsl(var(--knd-amber))"
          />
          <FeatureCard
            href="/regional-elo"
            title="Leaderboard"
            description="Global Elo by default, with optional state-assigned leaderboard views"
            color="hsl(var(--knd-lime))"
          />
          <FeatureCard
            href="/about"
            title="Methodology"
            description="Statistics, formulas, and how it all works"
            color="hsl(var(--knd-line))"
          />
        </section>
      </main>
    </div>
  );
}
