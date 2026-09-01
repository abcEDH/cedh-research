import Link from "next/link";
import { notFound } from "next/navigation";
import { normalizeDisplayString } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import TrendMetricCharts from "@/components/commanders/trend-metric-charts";
import CommanderMatchupsTable from "@/components/commanders/commander-matchups-table";
import { StatCard, ColorBadge } from "@/components/commanders/stat-card";
import { CommanderArt } from "@/components/commanders/commander-art";
import { CommanderHeaderBackdrop } from "@/components/commanders/commander-header-backdrop";
import { MomentumCard } from "@/components/commanders/momentum-card";
import { PerformanceCardRow } from "@/components/commanders/card-performance-row";
import { RecentFinishRow } from "@/components/commanders/recent-finish-row";
import { NotablePlayersTable } from "@/components/commanders/notable-players-table";
import { TrendSnapshotTables } from "@/components/commanders/trend-snapshot-tables";
import { CardFrequenciesTable } from "@/components/commanders/card-frequencies-table";
import {
  getCommanderDetails,
  getCardReport,
  getCardPerformance,
  getNotablePlayers,
  getCommanderMatchups,
  getRecentFinishes,
  getFirstPlaceFinishes,
  getCommanderTrendSeries,
  getCommanderMomentum,
  getCommanderArtByName,
} from "@/lib/commanders/fetchers";

export const revalidate = 3600;

export default async function CommanderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const commander = await getCommanderDetails(id);

  if (!commander) {
    notFound();
  }

  const [
    cardReport,
    cardPerformance,
    notablePlayers,
    matchups,
    recentFinishes,
    firstPlaceFinishes,
    trendSeries,
    momentum,
    commanderArt,
  ] = await Promise.all([
    getCardReport(id),
    getCardPerformance(id),
    getNotablePlayers(id),
    getCommanderMatchups(id),
    getRecentFinishes(id),
    getFirstPlaceFinishes(id),
    getCommanderTrendSeries(id),
    getCommanderMomentum(id),
    getCommanderArtByName(commander.commander_name),
  ]);

  const topPerformingCards = cardPerformance
    .filter((c) => parseFloat(c.win_rate_delta) > 0)
    .slice(0, 20);
  const underperformingCards = cardPerformance
    .filter((c) => parseFloat(c.win_rate_delta) < 0)
    .sort((a, b) => parseFloat(a.win_rate_delta) - parseFloat(b.win_rate_delta))
    .slice(0, 20);

  const cardPerformanceMap = new Map(cardPerformance.map((cp) => [cp.card_name, cp]));

  const winRateValue = parseFloat(commander.avg_win_rate);
  const totalGames = commander.total_wins + commander.total_losses + commander.total_draws;
  const pointsPerGame = totalGames > 0 ? (commander.total_wins * 5 + commander.total_draws) / totalGames : 0;
  const resiliencyRate = totalGames > 0 ? (commander.total_wins + commander.total_draws) / totalGames : 0;
  const baselinePointsPerGame = 1.25;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <CommanderHeaderBackdrop name={commander.commander_name} />
          <div className="knd-watermark absolute inset-0" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_80%_at_80%_0%,hsl(var(--knd-magenta)/0.18),transparent_60%)]" />
          <div className="relative">
            <Link href="/commanders" className="text-sm text-muted-foreground hover:text-foreground">
              ← Back to Commanders
            </Link>
            <div className="mt-5 grid gap-6 lg:grid-cols-[auto_1fr] lg:items-center">
              <CommanderArt name={commander.commander_name} size={112} artByName={commanderArt} />
              <div>
                <div className="flex items-center gap-3">
                  {commander.color_identity?.filter(Boolean).map((color) => (
                    <ColorBadge key={color} color={color} size="lg" />
                  ))}
                </div>
                <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
                  {normalizeDisplayString(commander.commander_name)}
                </h1>
                {commander.archetype && (
                  <p className="text-muted-foreground mt-1">
                    {normalizeDisplayString(commander.archetype)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stat grid */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6 mb-8">
          <StatCard label="Total Entries" value={commander.total_entries.toLocaleString()} tone="neutral" tooltip="Number of tournament entries for this commander." />
          <StatCard label="Tournaments" value={commander.tournaments_played.toString()} tone="neutral" tooltip="Unique tournaments where this commander was played." />
          <StatCard label="Win Rate" value={`${(winRateValue * 100).toFixed(1)}%`} tone={winRateValue > 0.25 ? "primary" : "neutral"} tooltip="Wins divided by total games. Baseline in 4-player pods is 25%." />
          <StatCard label="Points / Game" value={pointsPerGame.toFixed(2)} tone={pointsPerGame > baselinePointsPerGame ? "primary" : "neutral"} tooltip="Weighted average points per game: win=5, draw=1, loss=0." />
          <StatCard label="Top 16 / Top 10 / Top 4 Rate" value={`${(parseFloat(commander.conversion_rate_top_16) * 100).toFixed(1)}%`} tone="neutral" tooltip="Share of entries reaching the top bracket. Under 64 players, events may have a Top 10, and for 34 players or fewer we only count Top 4 finishes." />
          <StatCard label="Top Cut Conversion" value={`${(parseFloat(commander.conversion_rate_top_cut) * 100).toFixed(1)}%`} tone="neutral" tooltip="Share of entries reaching the event's top cut bracket." />
          <StatCard label="1st Place Finishes" value={firstPlaceFinishes.toLocaleString()} tone="neutral" tooltip="Count of tournament entries finishing in 1st place." />
          <StatCard label="Resiliency" value={`${(resiliencyRate * 100).toFixed(1)}%`} tone={resiliencyRate > 0.25 ? "primary" : "neutral"} tooltip="Win + draw rate. Higher means fewer losses." />
          <StatCard label="Total Wins" value={commander.total_wins.toLocaleString()} tone="neutral" tooltip="Total wins across all recorded games." />
          <StatCard label="W/L/D" value={`${commander.total_wins}/${commander.total_losses}/${commander.total_draws}`} tone="neutral" tooltip="Wins, losses, and draws recorded for this commander." />
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="flex flex-wrap gap-1 rounded-xl border border-border/70 bg-card/60 p-1">
            <TabsTrigger value="overview" className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground">
              Overview
            </TabsTrigger>
            <TabsTrigger value="performance" className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground">
              Card Performance
            </TabsTrigger>
            <TabsTrigger value="cards" className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground">
              Card Frequencies ({cardReport.length})
            </TabsTrigger>
            {notablePlayers.length > 0 && (
              <TabsTrigger value="players" className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground">
                Notable Players ({notablePlayers.length})
              </TabsTrigger>
            )}
            {matchups.length > 0 && (
              <TabsTrigger value="matchups" className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground">
                Matchups
              </TabsTrigger>
            )}
          </TabsList>

          {/* Overview tab */}
          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Performance Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Actual Win Rate</span>
                    <span
                      className={`font-mono font-semibold ${
                        winRateValue > 0.25
                          ? "text-primary"
                          : winRateValue < 0.2
                            ? "text-[hsl(var(--knd-amber))]"
                            : "text-muted-foreground"
                      }`}
                    >
                      {(winRateValue * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Points / Game (W=5, D=1, L=0)</span>
                    <span className={`font-mono font-semibold ${pointsPerGame > baselinePointsPerGame ? "text-primary" : "text-muted-foreground"}`}>
                      {pointsPerGame.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Resiliency (Win + Draw)</span>
                    <span className={`font-mono ${resiliencyRate > 0.25 ? "text-primary" : "text-muted-foreground"}`}>
                      {(resiliencyRate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <hr className="border-border/60" />
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Top Bracket Finishes (Top 16/10/4)</span>
                    <span className="font-mono text-muted-foreground">{commander.top_16_count}</span>
                  </div>
                </CardContent>
              </Card>

              {momentum && <MomentumCard momentum={momentum} />}
            </div>

            <div className="mt-6">
              <TrendMetricCharts
                series={trendSeries}
                title="Commander trendlines"
                description="Weekly and monthly trends for entries, win rate, and points per game."
              />
            </div>

            <TrendSnapshotTables
              weeklyTable={trendSeries.weeklyTable}
              monthlyTable={trendSeries.monthlyTable}
            />

            {recentFinishes.length > 0 && (
              <Card className="mt-6">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Top Finishes (Past 30 Days)</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Top 16, Top Cut, and 1st-place finishes from the past month (Top 4 for 34-player events).
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {recentFinishes.map((finish) => (
                      <RecentFinishRow key={finish.id} finish={finish} />
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Card Performance tab */}
          <TabsContent value="performance" className="mt-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="border-l-2 border-l-[hsl(var(--knd-cyan))]">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg text-primary">Top Performing Cards</CardTitle>
                  <p className="text-sm text-muted-foreground">Cards that correlate with higher win rates.</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {topPerformingCards.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Insufficient data for analysis.</p>
                    ) : (
                      topPerformingCards.map((card) => (
                        <PerformanceCardRow key={card.card_name} card={card} />
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-l-2 border-l-[hsl(var(--knd-amber))]">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg text-[hsl(var(--knd-amber))]">Underperforming Cards</CardTitle>
                  <p className="text-sm text-muted-foreground">Cards that correlate with lower win rates.</p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {underperformingCards.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Insufficient data for analysis.</p>
                    ) : (
                      underperformingCards.map((card) => (
                        <PerformanceCardRow key={card.card_name} card={card} isNegative />
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="mt-6">
              <CardContent className="pt-6">
                <p className="text-sm text-muted-foreground">
                  <strong className="text-foreground">Note:</strong> Win rate delta shows the difference
                  between average win rate of decks running this card vs the commander&apos;s baseline.
                  Cards with higher standard deviation have less certainty. Requires minimum 3 deck appearances.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notable Players tab */}
          {notablePlayers.length > 0 && (
            <TabsContent value="players" className="mt-6">
              <NotablePlayersTable players={notablePlayers} commanderName={commander.commander_name} />
            </TabsContent>
          )}

          {/* Matchups tab */}
          {matchups.length > 0 && (
            <TabsContent value="matchups" className="mt-6">
              <CommanderMatchupsTable matchups={matchups} />
              <Card className="mt-6">
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    <strong className="text-foreground">Note:</strong> Matchup data shows results when both
                    commanders appear in the same pod. In 4-player pods, only direct wins against that
                    opponent are counted.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Card Frequencies tab */}
          <TabsContent value="cards" className="mt-6">
            <CardFrequenciesTable
              commanderName={commander.commander_name}
              cardReport={cardReport}
              cardPerformanceMap={cardPerformanceMap}
            />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
