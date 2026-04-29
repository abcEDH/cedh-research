import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { unstable_cache } from "next/cache";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import Link from "next/link";
import { HomeSearchBar } from "@/components/home-search-bar";

const HOME_CACHE_REVALIDATE_SECONDS = 60 * 60 * 6; // 6 hours

export const dynamic = "force-dynamic";

interface TopCommander {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: number;
  conversion_rate_top_16: number;
  color_identity: string[] | null;
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
}

function addDaysIso(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00.000Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function isKnownCommanderName(value: string | null | undefined): value is string {
  const normalized = (value ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

/**
 * Orders commanders by the largest gain in weekly tournament entries: sums the two most recent
 * ISO weeks from `commander_weekly_trends` and subtracts the sum for the two weeks before that
 * (32+ player events; same filter as the materialized view).
 */
async function getTopRisingCommandersByTwoWeekTrend(): Promise<RisingCommander[]> {
  const { data: maxRows, error: maxErr } = await supabase
    .from("commander_weekly_trends")
    .select("week_start_date")
    .not("commander_name", "ilike", "unknown commander")
    .not("commander_name", "is", null)
    .neq("commander_name", "")
    .order("week_start_date", { ascending: false })
    .limit(1);

  if (maxErr) {
    throw new Error(`Rising commanders max week query failed: ${maxErr.message}`);
  }
  if (!maxRows?.[0]?.week_start_date) return [];

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

  if (trendErr) {
    throw new Error(`Rising commanders trends window query failed: ${trendErr.message}`);
  }
  if (!trendRows?.length) return [];

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
    throw new Error(`Rising commanders enrich query failed: ${metaErr.message}`);
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
}

async function getCoreStats() {
  const [topCommandersResult, topWinRateResult] = await Promise.all([
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
  ]);

  if (topCommandersResult.error) {
    throw new Error(`Top commanders query failed: ${topCommandersResult.error.message}`);
  }
  if (topWinRateResult.error) {
    throw new Error(`Top win rate query failed: ${topWinRateResult.error.message}`);
  }

  return {
    topCommanders: ((topCommandersResult.data ?? []) as TopCommander[]).filter((row) =>
      isKnownCommanderName(row.commander_name)
    ),
    topWinRate: ((topWinRateResult.data ?? []) as TopCommander[]).filter((row) =>
      isKnownCommanderName(row.commander_name)
    ),
  };
}

const getCachedHomeCoreStats = unstable_cache(
  getCoreStats,
  ["home-core-stats-v3"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

const getCachedHomeRisingCommanders = unstable_cache(
  getTopRisingCommandersByTwoWeekTrend,
  ["home-rising-commanders-v1"],
  { revalidate: HOME_CACHE_REVALIDATE_SECONDS }
);

export default async function Home() {
  const [{ topCommanders, topWinRate }, topRisingCommanders] = await Promise.all([
    getCachedHomeCoreStats(),
    getCachedHomeRisingCommanders().catch((error) => {
      console.error("Home rising commanders cache refresh failed:", error);
      return [];
    }),
  ]);
  const topThreePopular: TopCommander[] = topCommanders.slice(0, 3);
  const showTrendCards = topThreePopular.length > 0 || topRisingCommanders.length > 0;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 pb-24 pt-10">
        <header className="flex flex-col gap-6 border-b border-border/60 pb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-foreground md:text-4xl">tedh.gg</h1>
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
              Competitive Commander, simplified
            </h2>
            <p className="text-base text-muted-foreground">
              tedh.gg keeps the cEDH field, leaders, and trends in one place.
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

        {showTrendCards ? (
          <section className="mt-12 grid gap-6 lg:grid-cols-2">
            {topThreePopular.length > 0 ? (
              <Card data-testid="top-popular-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Top 3 most popular commanders</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Ranked by total entries in large events.
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
            {topRisingCommanders.length > 0 ? (
              <Card data-testid="top-rising-commanders" className="min-w-0">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Biggest popularity gain (2 weeks)</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Extra tournament entries in the latest two ISO weeks vs the stretch before that.
                  </p>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {topRisingCommanders.map((commander, index) => (
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
                  {topCommanders.length > 0 ? (
                    topCommanders.map((commander, index) => (
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
                    ))
                  ) : (
                    <TableRow className="border-border/60">
                      <TableCell className="py-6 text-sm text-muted-foreground" colSpan={5}>
                        No commander data available right now.
                      </TableCell>
                    </TableRow>
                  )}
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
              {topWinRate.length > 0 ? (
                topWinRate.map((commander, index) => (
                  <CommanderRow key={commander.commander_id} commander={commander} rank={index + 1} />
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No win-rate data available right now.</p>
              )}
              <Button asChild variant="ghost" className="w-full border border-border/70">
                <Link href="/commanders">View all commanders</Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        <section data-testid="home-feature-cards" className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          <FeatureCard
            href="/commanders"
            title="Commander Rankings"
            description="Sortable performance data for all commanders"
            color="hsl(var(--knd-cyan))"
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

function RisingCommanderRow({
  commander,
  rank,
}: {
  commander: RisingCommander;
  rank: number;
}) {
  const winRate = (commander.avg_win_rate * 100).toFixed(1);
  const isAboveExpected = commander.avg_win_rate > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 pt-0.5 font-mono text-xs text-muted-foreground">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-1 pt-0.5">
        {commander.color_identity?.filter(Boolean).map((color: string) => (
          <ColorBadge key={color} color={color} />
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <p className="break-words text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="break-words text-xs text-muted-foreground">
          {commander.recent_entries} latest stretch · prior {commander.prior_entries} ·{" "}
          <span className={isAboveExpected ? "text-primary" : undefined}>{winRate}%</span> win
        </p>
      </div>
      <div className="shrink-0 self-start text-right">
        <p className="font-mono text-sm text-primary">+{(commander.meta_share_delta * 100).toFixed(2)}%</p>
        <p className="text-xs text-muted-foreground">meta share</p>
      </div>
    </Link>
  );
}
function CommanderRow({
  commander,
  rank,
}: {
  commander: TopCommander;
  rank: number;
}) {
  const winRate = (commander.avg_win_rate * 100).toFixed(1);
  const isAboveExpected = commander.avg_win_rate > 0.25;

  return (
    <Link
      href={`/commanders/${commander.commander_id}`}
      className="flex w-full min-w-0 items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <span className="shrink-0 pt-0.5 font-mono text-xs text-muted-foreground">#{rank}</span>
      <div className="flex shrink-0 flex-wrap gap-1 pt-0.5">
        {commander.color_identity?.filter(Boolean).map((color: string) => (
          <ColorBadge key={color} color={color} />
        ))}
      </div>
      <div className="min-w-0 flex-1">
        <p className="break-words text-sm font-medium text-foreground">
          {normalizeDisplayString(commander.commander_name)}
        </p>
        <p className="break-words text-xs text-muted-foreground">{commander.total_entries} entries</p>
      </div>
      <div className="shrink-0 self-start text-right">
        <p className={`font-mono text-sm ${isAboveExpected ? "text-primary" : "text-muted-foreground"}`}>
          {winRate}%
        </p>
        <p className="text-xs text-muted-foreground">win rate</p>
      </div>
    </Link>
  );
}

function ColorBadge({ color }: { color: string }) {
  const colors: Record<string, string> = {
    W: "bg-amber-200/80 text-amber-950",
    U: "bg-sky-500/90 text-white",
    B: "bg-purple-900/90 text-purple-100",
    R: "bg-red-500/90 text-white",
    G: "bg-emerald-500/90 text-white",
  };

  return (
    <span
      className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
        colors[color] || "bg-slate-500 text-white"
      }`}
    >
      {color}
    </span>
  );
}

function FeatureCard({
  href,
  title,
  description,
  color,
}: {
  href: string;
  title: string;
  description: string;
  color: string;
}) {
  return (
    <Link href={href}>
      <Card className="h-full border-border/60 transition hover:border-primary/40">
        <CardHeader>
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{description}</p>
        </CardContent>
      </Card>
    </Link>
  );
}
