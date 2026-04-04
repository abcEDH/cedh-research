import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { fetchChampionshipLeaderboard } from "@/lib/topdeck";
import { buildTopdeckProfileHref } from "@/lib/topdeck-profile";

// Force dynamic rendering - fetch fresh data on each request
export const dynamic = "force-dynamic";

interface TopCommander {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: number;
  conversion_rate_top_16: number;
  color_identity: string[] | null;
}

async function getStats() {
  try {
    const [tournamentResult, commanderResult, topCommandersResult, topWinRateResult] =
      await Promise.all([
        supabase.from("tournaments").select("*", { count: "exact", head: true }),
        supabase.from("commanders").select("*", { count: "exact", head: true }),
        supabase
          .from("commander_stats")
          .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_16, color_identity")
          .gt("total_entries", 20)
          .order("total_entries", { ascending: false })
          .limit(21),
        supabase
          .from("commander_stats")
          .select("commander_id, commander_name, total_entries, avg_win_rate, conversion_rate_top_16, color_identity")
          .gt("total_entries", 30)
          .order("avg_win_rate", { ascending: false })
          .limit(10),
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
      topCommanders: (topCommandersResult.data ?? []) as TopCommander[],
      topWinRate: (topWinRateResult.data ?? []) as TopCommander[],
      topPlayers,
    };
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return {
      tournamentCount: 0,
      commanderCount: 0,
      topCommanders: [],
      topWinRate: [],
      topPlayers: [],
    };
  }
}

export default async function Home() {
  const { topCommanders, topWinRate, topPlayers } = await getStats();
  const filteredCommanders = topCommanders.filter(
    (commander) => commander.commander_name?.toLowerCase() !== "unknown commander"
  );
  const filteredWinRate = topWinRate.filter(
    (commander) => commander.commander_name?.toLowerCase() !== "unknown commander"
  );

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
              <Link className="transition hover:text-foreground" href="/cards">
                Cards
              </Link>
              <Link className="transition hover:text-foreground" href="/turn-order">
                Turn Order
              </Link>
              <Link className="transition hover:text-foreground" href="/survival">
                Survival
              </Link>
              <Link className="transition hover:text-foreground" href="/tournament-likelihood">
                Tournament Prep
              </Link>
              <Link className="transition hover:text-foreground" href="/regional-elo">
                Regional Elo
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

        <section className="mt-10">
          <div className="max-w-3xl space-y-6">
            <div className="space-y-4">
              <h2 className="text-4xl font-semibold leading-tight text-foreground md:text-5xl">
                A clean command layer for competitive Commander analytics.
              </h2>
              <p className="text-lg text-muted-foreground">
                Track meta shifts, conversion rates, and archetype pressure with an interface tuned for fast reads and
                deep dives.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/commanders">Open dashboard</Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="border-border/70 bg-muted/30">
                <Link href="/about">View methodology</Link>
              </Button>
            </div>
          </div>
        </section>

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
                  {filteredCommanders.map((commander, index) => (
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
              {filteredWinRate.map((commander, index) => (
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
              <Button asChild variant="ghost" className="mt-4 w-full border border-border/70">
                <Link href="/midseason-invitational">Open current top-100 breakdown</Link>
              </Button>
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
            href="/cards"
            title="Card Frequency"
            description="Global card inclusion rates and tiers"
            color="hsl(var(--knd-amber))"
          />
          <FeatureCard
            href="/turn-order"
            title="Turn Order Fairness"
            description="Statistical analysis of seat position advantage"
            color="hsl(var(--knd-cyan))"
          />
          <FeatureCard
            href="/trap-spice"
            title="Trap & Spice Cards"
            description="Find overrated and underrated cards"
            color="hsl(var(--knd-amber))"
          />
          <FeatureCard
            href="/survival"
            title="Survival Analysis"
            description="Track survival probability through tournament rounds"
            color="hsl(var(--knd-cyan))"
          />
          <FeatureCard
            href="/tournament-likelihood"
            title="Tournament Prep"
            description="Estimate attendee commander likelihood and expected meta share"
            color="hsl(var(--knd-amber))"
          />
          <FeatureCard
            href="/midseason-invitational"
            title="TopDeck Top 100"
            description="Current TopDeck leaderboard and most-played deck profiles"
            color="hsl(var(--knd-cyan))"
          />
          <FeatureCard
            href="/regional-elo"
            title="Regional Elo"
            description="State-level Elo leaderboards using localized tournament results"
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

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "cyan" | "amber" | "neutral";
}) {
  const toneMap: Record<typeof tone, string> = {
    cyan: "text-primary",
    amber: "text-[hsl(var(--knd-amber))]",
    neutral: "text-muted-foreground",
  };

  return (
    <div className="rounded-xl border border-border/70 bg-muted/30 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <div className="mt-3 flex items-center justify-between">
        <span className={`text-2xl font-semibold ${toneMap[tone]}`}>{value}</span>
      </div>
    </div>
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
      className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-3 transition hover:border-primary/40 hover:bg-muted/50"
    >
      <div className="flex items-center gap-3">
        <span className="w-6 font-mono text-xs text-muted-foreground">#{rank}</span>
        <div className="flex gap-1">
          {commander.color_identity?.filter(Boolean).map((color: string) => (
            <ColorBadge key={color} color={color} />
          ))}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {normalizeDisplayString(commander.commander_name)}
          </p>
          <p className="text-xs text-muted-foreground">{commander.total_entries} entries</p>
        </div>
      </div>
      <div className="text-right">
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
