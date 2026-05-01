import Link from "next/link";
import { notFound } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { normalizeDisplayString } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import TrendMetricCharts, {
  TrendMetricPoint,
  TrendMetricSeries,
} from "@/components/commanders/trend-metric-charts";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import CommanderMatchupsTable, {
  CommanderMatchup as CommanderMatchupType,
} from "@/components/commanders/commander-matchups-table";

export const dynamic = "force-dynamic";

function normalCdf(x: number) {
  const sign = x >= 0 ? 1 : -1;
  const absX = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * absX);
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const erf =
    1 -
    (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t) *
      Math.exp(-absX * absX);
  return 0.5 * (1 + sign * erf);
}

function formatPValue(pValue: number) {
  if (pValue < 0.001) return "<0.001";
  if (pValue < 0.01) return "<0.01";
  return pValue.toFixed(3);
}

interface CommanderStat {
  commander_id: string;
  commander_name: string;
  archetype: string | null;
  color_identity: string[] | null;
  total_entries: number;
  tournaments_played: number;
  total_wins: number;
  total_losses: number;
  total_draws: number;
  avg_win_rate: string;
  top_16_count: number;
  conversion_rate_top_16: string;
  top_cut_count: number;
  conversion_rate_top_cut: string;
}

interface CommanderMeta {
  scryfall_ids: string[] | null;
  commander_names: string[] | null;
}

type TrendRow = {
  week_key?: string | null;
  week_start_date?: string | null;
  month_key?: string | null;
  entries: number;
  wins?: number | null;
  losses?: number | null;
  draws?: number | null;
  total_players?: number | null;
};

function normalizeDateKey(value: string | null | undefined) {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

interface CardReport {
  commander: string;
  commander_id: string;
  card_name: string;
  deck_count: number;
  total_decks: number;
  inclusion_rate: string;
  tier: string;
  global_rate: string;
  synergy_score: string;
}

interface CardPerformance {
  commander_id: string;
  commander: string;
  card_name: string;
  deck_count: number;
  total_decks: number;
  inclusion_rate: string;
  avg_win_rate: string;
  baseline_win_rate: string;
  win_rate_delta: string;
  std_win_rate: string;
  top_16_count: number;
  top_16_rate: string;
  performance_tier: string;
}

interface NotablePlayer {
  player_name: string;
  topdeck_id: string | null;
  entries: number;
  total_wins: number;
  total_games: number;
  win_rate: string | null;
  top_16_count: number;
}

interface RecentFinish {
  id: string;
  final_standing: number | null;
  made_top_cut: boolean;
  made_top_16: boolean;
  decklist_url: string | null;
  player_name: string | null;
  player_handle: string | null;
  player_id: string | null;
  tournament: {
    id: string;
    name: string;
    start_date: string;
    player_count: number;
    top_cut: number;
    topdeck_tid: string;
  };
}

async function getCommanderDetails(id: string) {
  const { data, error } = await supabase
    .from("commander_stats")
    .select("*")
    .eq("commander_id", id)
    .single();

  if (error || !data) {
    return null;
  }
  return data as CommanderStat;
}

async function getCommanderMeta(id: string) {
  const { data, error } = await supabase
    .from("commanders")
    .select("scryfall_ids, commander_names")
    .eq("id", id)
    .single();

  if (error || !data) {
    return null;
  }
  return data as CommanderMeta;
}

async function getRecentFinishes(commanderId: string, daysBack: number = 30) {
  // Filter tournaments from the past N days
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - daysBack);
  const cutoffIso = cutoffDate.toISOString();

  const { data, error } = await supabase
    .from("tournament_entries")
    .select(
      "id, final_standing, made_top_cut, made_top_16, decklist_url, tournaments ( id, name, start_date, player_count, top_cut, topdeck_tid ), players ( name, topdeck_handle, topdeck_id )"
    )
    .eq("commander_id", commanderId)
    .or("made_top_16.eq.true,made_top_cut.eq.true,final_standing.eq.1")
    .gte("tournaments.start_date", cutoffIso)
    .order("start_date", { ascending: false, foreignTable: "tournaments" });

  if (error) {
    console.error("Error fetching recent finishes:", error);
    return [];
  }

  const finishes = (data || [])
    .map((row) => {
      const tournament = Array.isArray(row.tournaments)
        ? row.tournaments[0]
        : row.tournaments;
      const player = Array.isArray(row.players) ? row.players[0] : row.players;
      if (!tournament) return null;
      return {
        id: row.id,
        final_standing: row.final_standing,
        made_top_cut: row.made_top_cut,
        made_top_16: row.made_top_16,
        decklist_url: row.decklist_url,
        player_name: player?.name ?? null,
        player_handle: player?.topdeck_handle ?? null,
        player_id: player?.topdeck_id ?? null,
        tournament,
      } as RecentFinish;
    })
    .filter((row): row is RecentFinish => row !== null);

  finishes.sort((a, b) => {
    const dateA = new Date(a.tournament.start_date).getTime();
    const dateB = new Date(b.tournament.start_date).getTime();
    return dateB - dateA;
  });

  const grouped = new Map<string, RecentFinish>();
  for (const finish of finishes) {
    const key = finish.decklist_url ?? finish.id;
    if (!grouped.has(key)) {
      grouped.set(key, finish);
    }
  }

  // Show up to 20 top finishes from the past 30 days
  return Array.from(grouped.values()).slice(0, 20);
}

async function getCardReport(commanderId: string) {
  const { data, error } = await supabase
    .from("commander_card_report")
    .select("*")
    .eq("commander_id", commanderId)
    .order("inclusion_rate", { ascending: false });

  if (error) {
    console.error("Error fetching card report:", error);
    return [];
  }
  return data as CardReport[];
}

async function getCardPerformance(commanderId: string) {
  const { data, error } = await supabase
    .from("card_performance_by_commander")
    .select("*")
    .eq("commander_id", commanderId)
    .gte("deck_count", 3)
    .order("win_rate_delta", { ascending: false });

  if (error) {
    console.error("Error fetching card performance:", error);
    return [];
  }
  return data as CardPerformance[];
}

async function getNotablePlayers(commanderId: string): Promise<NotablePlayer[]> {
  const { data, error } = await supabase.rpc("get_notable_players_for_commander", {
    p_commander_id: commanderId,
  });

  if (error) {
    console.error("Error fetching notable players:", error);
    return [];
  }
  return data as NotablePlayer[];
}

async function getCommanderMatchups(commanderId: string): Promise<CommanderMatchupType[]> {
  const { data, error } = await supabase.rpc("get_commander_matchups", {
    p_commander_id: commanderId,
  });

  if (error) {
    console.error("Error fetching matchups:", error);
    return [];
  }
  return data as CommanderMatchupType[];
}

type CommanderTrendTableRow = {
  period: string;
  entries: number;
  players: number | null;
  winRate: number;
  pointsPerGame: number;
};

async function getCommanderTrendSeries(commanderId: string) {
  const weeklyPrimary = await supabase
    .from("commander_weekly_trends")
    .select("week_key, week_start_date, entries, wins, losses, draws, total_players")
    .eq("commander_id", commanderId)
    .order("week_start_date", { ascending: true });

  const monthlyPrimary = await supabase
    .from("commander_monthly_trends")
    .select("month_key, entries, wins, losses, draws, total_players")
    .eq("commander_id", commanderId)
    .order("month_key", { ascending: true });

  let weeklyData: TrendRow[] = weeklyPrimary.data ?? [];
  let monthlyData: TrendRow[] = monthlyPrimary.data ?? [];

  if (weeklyPrimary.error) {
    console.error("Error fetching weekly trends (with players):", weeklyPrimary.error);
    const weeklyFallback = await supabase
      .from("commander_weekly_trends")
      .select("week_key, week_start_date, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .order("week_start_date", { ascending: true });
    weeklyData = weeklyFallback.data ?? [];
  }

  if (monthlyPrimary.error) {
    console.error("Error fetching monthly trends (with players):", monthlyPrimary.error);
    const monthlyFallback = await supabase
      .from("commander_monthly_trends")
      .select("month_key, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .order("month_key", { ascending: true });
    monthlyData = monthlyFallback.data ?? [];
  }

  if (weeklyPrimary.error) {
    console.error("Error fetching commander weekly trends:", weeklyPrimary.error);
  }
  if (monthlyPrimary.error) {
    console.error("Error fetching commander monthly trends:", monthlyPrimary.error);
  }

  const weeklyRows = (weeklyData || []) as {
    week_key?: string | null;
    week_start_date?: string | null;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
    total_players?: number | null;
  }[];
  const monthlyRows = (monthlyData || []) as {
    month_key: string;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
    total_players?: number | null;
  }[];

  const weekly: TrendMetricPoint[] = weeklyRows
    .filter((row) => row.wins + row.losses + row.draws > 0)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      const winRate = games ? (row.wins / games) * 100 : 0;
      const pointsPerGame = games ? (row.wins * 5 + row.draws) / games : 0;
      return { period: normalizeDateKey(row.week_start_date) || row.week_key || "", entries: row.entries, winRate, pointsPerGame };
    });

  const monthly: TrendMetricPoint[] = monthlyRows
    .filter((row) => row.wins + row.losses + row.draws > 0)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      const winRate = games ? (row.wins / games) * 100 : 0;
      const pointsPerGame = games ? (row.wins * 5 + row.draws) / games : 0;
      return { period: row.month_key, entries: row.entries, winRate, pointsPerGame };
    });

  const weeklyTable: CommanderTrendTableRow[] = weeklyRows
    .filter((row) => row.wins + row.losses + row.draws > 0)
    .slice(-52)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      const winRate = games ? (row.wins / games) * 100 : 0;
      const pointsPerGame = games ? (row.wins * 5 + row.draws) / games : 0;
      return {
        period: normalizeDateKey(row.week_start_date) || row.week_key || "",
        entries: row.entries,
        players: row.total_players ?? null,
        winRate,
        pointsPerGame,
      };
    });

  const monthlyTable: CommanderTrendTableRow[] = monthlyRows
    .filter((row) => row.wins + row.losses + row.draws > 0)
    .slice(-52)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      const winRate = games ? (row.wins / games) * 100 : 0;
      const pointsPerGame = games ? (row.wins * 5 + row.draws) / games : 0;
      return {
        period: row.month_key,
        entries: row.entries,
        players: row.total_players ?? null,
        winRate,
        pointsPerGame,
      };
    });

  return { weekly, monthly, weeklyTable, monthlyTable } satisfies TrendMetricSeries & {
    weeklyTable: CommanderTrendTableRow[];
    monthlyTable: CommanderTrendTableRow[];
  };
}

async function getFirstPlaceFinishes(commanderId: string): Promise<number> {
  const { count, error } = await supabase
    .from("tournament_entries")
    .select("*", { count: "exact", head: true })
    .eq("commander_id", commanderId)
    .eq("final_standing", 1);

  if (error) {
    console.error("Error fetching first-place finishes:", error);
    return 0;
  }

  return count ?? 0;
}

export default async function CommanderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [commander, commanderMeta] = await Promise.all([
    getCommanderDetails(id),
    getCommanderMeta(id),
  ]);

  if (!commander) {
    notFound();
  }

  const [cardReport, cardPerformance, notablePlayers, matchups, recentFinishes, firstPlaceFinishes, trendSeries] = await Promise.all([
    getCardReport(id),
    getCardPerformance(id),
    getNotablePlayers(id),
    getCommanderMatchups(id),
    getRecentFinishes(id),
    getFirstPlaceFinishes(id),
    getCommanderTrendSeries(id),
  ]);

  const topPerformingCards = cardPerformance
    .filter((c) => parseFloat(c.win_rate_delta) > 0)
    .slice(0, 20);
  const underperformingCards = cardPerformance
    .filter((c) => parseFloat(c.win_rate_delta) < 0)
    .sort((a, b) => parseFloat(a.win_rate_delta) - parseFloat(b.win_rate_delta))
    .slice(0, 20);

  const cardPerformanceMap = new Map(
    cardPerformance.map((cp) => [cp.card_name, cp])
  );

  const winRateValue = parseFloat(commander.avg_win_rate);
  const totalGames = commander.total_wins + commander.total_losses + commander.total_draws;
  const pointsPerGame = totalGames > 0 ? (commander.total_wins * 5 + commander.total_draws) / totalGames : 0;
  const resiliencyRate = totalGames > 0 ? (commander.total_wins + commander.total_draws) / totalGames : 0;
  const baselinePointsPerGame = 1.25;

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link
              href="/commanders"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Commanders
            </Link>
            <div className="mt-5 grid gap-6 lg:grid-cols-[auto_1fr] lg:items-center">
              {commanderMeta?.scryfall_ids && commanderMeta.scryfall_ids.length > 0 && (
                <div className="flex items-center gap-3">
                  {commanderMeta.scryfall_ids.slice(0, 2).map((scryfallId) => (
                    <img
                      key={scryfallId}
                      src={`https://cards.scryfall.io/art_crop/${scryfallId}.jpg`}
                      alt={normalizeDisplayString(commander.commander_name)}
                      className="h-28 w-28 rounded-xl border border-border/60 object-cover shadow-lg"
                      loading="lazy"
                    />
                  ))}
                </div>
              )}
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

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6 mb-8">
          <StatCard
            label="Total Entries"
            value={commander.total_entries.toLocaleString()}
            tone="neutral"
            tooltip="Number of tournament entries for this commander."
          />
          <StatCard
            label="Tournaments"
            value={commander.tournaments_played.toString()}
            tone="neutral"
            tooltip="Unique tournaments where this commander was played."
          />
          <StatCard
            label="Win Rate"
            value={`${(winRateValue * 100).toFixed(1)}%`}
            tone={winRateValue > 0.25 ? "primary" : "neutral"}
            tooltip="Wins divided by total games. Baseline in 4-player pods is 25%."
          />
          <StatCard
            label="Points / Game"
            value={pointsPerGame.toFixed(2)}
            tone={pointsPerGame > baselinePointsPerGame ? "primary" : "neutral"}
            tooltip="Weighted average points per game: win=5, draw=1, loss=0."
          />
          <StatCard
            label="Top 16 / Top 10 / Top 4 Rate"
            value={`${(parseFloat(commander.conversion_rate_top_16) * 100).toFixed(1)}%`}
            tone="neutral"
            tooltip="Share of entries reaching the top bracket. Under 64 players, events may have a Top 10, and for 34 players or fewer we only count Top 4 finishes."
          />
          <StatCard
            label="Top Cut Conversion"
            value={`${(parseFloat(commander.conversion_rate_top_cut) * 100).toFixed(1)}%`}
            tone="neutral"
            tooltip="Share of entries reaching the event's top cut bracket."
          />
          <StatCard
            label="1st Place Finishes"
            value={firstPlaceFinishes.toLocaleString()}
            tone="neutral"
            tooltip="Count of tournament entries finishing in 1st place."
          />
          <StatCard
            label="Resiliency"
            value={`${(resiliencyRate * 100).toFixed(1)}%`}
            tone={resiliencyRate > 0.25 ? "primary" : "neutral"}
            tooltip="Win + draw rate. Higher means fewer losses."
          />
          <StatCard
            label="Total Wins"
            value={commander.total_wins.toLocaleString()}
            tone="neutral"
            tooltip="Total wins across all recorded games."
          />
          <StatCard
            label="W/L/D"
            value={`${commander.total_wins}/${commander.total_losses}/${commander.total_draws}`}
            tone="neutral"
            tooltip="Wins, losses, and draws recorded for this commander."
          />
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="flex flex-wrap gap-1 rounded-xl border border-border/70 bg-card/60 p-1">
            <TabsTrigger
              value="overview"
              className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground"
            >
              Overview
            </TabsTrigger>
            <TabsTrigger
              value="performance"
              className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground"
            >
              Card Performance
            </TabsTrigger>
            <TabsTrigger
              value="cards"
              className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground"
            >
              Card Frequencies ({cardReport.length})
            </TabsTrigger>
            {notablePlayers.length > 0 && (
              <TabsTrigger
                value="players"
                className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground"
              >
                Notable Players ({notablePlayers.length})
              </TabsTrigger>
            )}
            {matchups.length > 0 && (
              <TabsTrigger
                value="matchups"
                className="data-[state=active]:bg-muted/60 data-[state=active]:text-foreground"
              >
                Matchups
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid grid-cols-1 gap-6">
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
                    <span className="font-mono text-muted-foreground">
                      {commander.top_16_count}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="mt-6">
              <TrendMetricCharts
                series={trendSeries}
                title="Commander trendlines"
                description="Weekly and monthly trends for entries, win rate, and points per game."
              />
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Weekly snapshot</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        <TableHead>Week</TableHead>
                        <TableHead className="text-right">Entries</TableHead>
                        <TableHead className="text-right">Win %</TableHead>
                        <TableHead className="text-right">Pts/Game</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trendSeries.weeklyTable.map((row) => (
                        <TableRow key={row.period} className="border-border/60">
                          <TableCell className="font-mono text-xs text-muted-foreground">{row.period}</TableCell>
                          <TableCell className="text-right font-mono">{row.entries}</TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {row.winRate.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {row.pointsPerGame.toFixed(2)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">Monthly snapshot</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        <TableHead>Month</TableHead>
                        <TableHead className="text-right">Entries</TableHead>
                        <TableHead className="text-right">Win %</TableHead>
                        <TableHead className="text-right">Pts/Game</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {trendSeries.monthlyTable.map((row) => (
                        <TableRow key={row.period} className="border-border/60">
                          <TableCell className="font-mono text-xs text-muted-foreground">{row.period}</TableCell>
                          <TableCell className="text-right font-mono">{row.entries}</TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {row.winRate.toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {row.pointsPerGame.toFixed(2)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>

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

          <TabsContent value="performance" className="mt-6">
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="border-l-2 border-l-[hsl(var(--knd-cyan))]">
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg text-primary">Top Performing Cards</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Cards that correlate with higher win rates.
                  </p>
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
                  <CardTitle className="text-lg text-[hsl(var(--knd-amber))]">
                    Underperforming Cards
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Cards that correlate with lower win rates.
                  </p>
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
                  <strong className="text-foreground">Note:</strong> Win rate delta shows the
                  difference between average win rate of decks running this card vs the commander&apos;s
                  baseline. Cards with higher standard deviation have less certainty. Requires minimum
                  3 deck appearances.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {notablePlayers.length > 0 && (
            <TabsContent value="players" className="mt-6">
              <Card>
                <CardHeader className="knd-panel-header">
                  <CardTitle className="text-lg">
                    Notable {normalizeDisplayString(commander.commander_name)} Players
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Players with 2+ tournament entries using this commander.
                  </p>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        <TableHead>Player</TableHead>
                        <TableHead className="text-right">Entries</TableHead>
                        <TableHead className="text-right">Games</TableHead>
                        <TableHead className="text-right">Win Rate</TableHead>
                        <TableHead className="text-right">Top 16/Top 4s</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {notablePlayers.map((player) => (
                        <TableRow key={player.player_name} className="border-border/60">
                          <TableCell className="font-medium">
                            {player.topdeck_id ? (
                              <a
                                href={`https://topdeck.gg/profile/${player.topdeck_id}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-foreground hover:text-primary"
                              >
                                {player.player_name}
                                <span className="ml-1 text-muted-foreground text-xs">↗</span>
                              </a>
                            ) : (
                              player.player_name
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono text-[hsl(var(--knd-amber))]">
                            {player.entries}
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {player.total_games}
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {player.win_rate ? (
                              <span
                                className={`${parseFloat(player.win_rate) > 0.25
                                  ? "text-primary"
                                  : parseFloat(player.win_rate) < 0.2
                                    ? "text-[hsl(var(--knd-amber))]"
                                    : "text-muted-foreground"}`}
                              >
                                {(parseFloat(player.win_rate) * 100).toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono text-[hsl(var(--knd-amber))]">
                            {player.top_16_count}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {matchups.length > 0 && (
            <TabsContent value="matchups" className="mt-6">
              <CommanderMatchupsTable matchups={matchups} />

              <Card className="mt-6">
                <CardContent className="pt-6">
                  <p className="text-sm text-muted-foreground">
                    <strong className="text-foreground">Note:</strong> Matchup data shows results when
                    both commanders appear in the same pod. In 4-player pods, only direct wins against that
                    opponent are counted.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          )}

          <TabsContent value="cards" className="mt-6">
            <Card>
              <CardHeader className="knd-panel-header">
                <CardTitle className="text-lg">
                  Card Frequencies for {normalizeDisplayString(commander.commander_name)}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/60 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <TableHead>Card Name</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead className="text-right">Inclusion</TableHead>
                      <TableHead className="text-right">Global Rate</TableHead>
                      <TableHead className="text-right">Win Rate Delta</TableHead>
                      <TableHead className="text-right">Decks</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cardReport.map((card) => {
                      const perf = cardPerformanceMap.get(card.card_name);
                      const winRateDelta = perf ? parseFloat(perf.win_rate_delta) * 100 : null;
                      return (
                        <TableRow key={card.card_name} className="border-border/60">
                          <TableCell className="font-medium">
                            <a
                              href={`https://scryfall.com/search?q=${encodeURIComponent(
                                normalizeDisplayString(card.card_name)
                              )}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-foreground hover:text-primary"
                            >
                              {normalizeDisplayString(card.card_name)}
                            </a>
                          </TableCell>
                          <TableCell>
                            <TierBadge tier={card.tier} />
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {(parseFloat(card.inclusion_rate) * 100).toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {(parseFloat(card.global_rate) * 100).toFixed(1)}%
                          </TableCell>
                          <TableCell className="text-right font-mono">
                            {winRateDelta !== null && perf ? (
                              <span className="inline-flex items-center gap-2">
                                <span
                                  className={`${winRateDelta > 0
                                    ? "text-primary"
                                    : winRateDelta < 0
                                      ? "text-[hsl(var(--knd-amber))]"
                                      : "text-muted-foreground"}`}
                                >
                                  {winRateDelta > 0 ? "+" : ""}
                                  {winRateDelta.toFixed(1)}%
                                </span>
                                {(() => {
                                  const stdDev = parseFloat(perf.std_win_rate) * 100;
                                  const zScore = winRateDelta / (stdDev / Math.sqrt(perf.deck_count));
                                  const pValue = 2 * (1 - normalCdf(Math.abs(zScore)));
                                  return (
                                    <span
                                      title="Two-sided p-value (normal approximation). Highlighted when p < 0.05."
                                      className={`rounded-full border px-2 py-0.5 text-[10px] ${
                                        pValue < 0.05
                                          ? "border-primary/40 text-primary"
                                          : "border-border/60 text-muted-foreground"
                                      }`}
                                    >
                                      p={formatPValue(pValue)}
                                    </span>
                                  );
                                })()}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right font-mono text-muted-foreground">
                            {card.deck_count}/{card.total_decks}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                <p className="mt-3 text-xs text-muted-foreground">
                  P-values are two-sided (normal approximation). Highlighted when p &lt; 0.05.
                </p>
                <p className="text-muted-foreground text-sm mt-4 text-center">
                  Showing all {cardReport.length} cards · {cardPerformance.length} have win rate data (min 3 decks)
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
  tooltip,
}: {
  label: string;
  value: string;
  tone: "primary" | "amber" | "neutral";
  tooltip?: string;
}) {
  const toneMap: Record<typeof tone, string> = {
    primary: "text-primary",
    amber: "text-[hsl(var(--knd-amber))]",
    neutral: "text-muted-foreground",
  };

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-center gap-2">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
          {tooltip && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="text-[10px] text-muted-foreground/80 hover:text-foreground"
                  aria-label={`More info about ${label}`}
                >
                  i
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs leading-relaxed">
                {tooltip}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <p
          className={`${
            value.length > 12 ? "text-lg" : "text-xl"
          } font-semibold ${toneMap[tone]}`}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  );
}

function ColorBadge({ color, size = "sm" }: { color: string; size?: "sm" | "lg" }) {
  const colors: Record<string, string> = {
    W: "bg-amber-200/80 text-amber-950",
    U: "bg-sky-500/90 text-white",
    B: "bg-purple-900/90 text-purple-100",
    R: "bg-red-500/90 text-white",
    G: "bg-emerald-500/90 text-white",
  };

  const sizeClass = size === "lg" ? "w-8 h-8 text-sm" : "w-5 h-5 text-xs";

  return (
    <span
      className={`${sizeClass} rounded-full flex items-center justify-center font-bold ${
        colors[color] || "bg-slate-500 text-white"
      }`}
    >
      {color}
    </span>
  );
}

function TierBadge({ tier }: { tier: string }) {
  const tierColors: Record<string, string> = {
    core: "bg-[hsl(var(--knd-cyan))]/15 text-primary border-primary/30",
    essential: "bg-[hsl(var(--knd-cyan))]/10 text-primary border-primary/20",
    common: "bg-[hsl(var(--knd-amber))]/15 text-[hsl(var(--knd-amber))] border-[hsl(var(--knd-amber))]/30",
    flex: "bg-muted/40 text-muted-foreground border-border/60",
    spice: "bg-muted/30 text-muted-foreground border-border/40",
  };

  return (
    <Badge
      variant="outline"
      className={tierColors[tier] || "bg-muted/30 text-muted-foreground border-border/40"}
    >
      {tier}
    </Badge>
  );
}

function PerformanceCardRow({
  card,
  isNegative = false,
}: {
  card: CardPerformance;
  isNegative?: boolean;
}) {
  const delta = parseFloat(card.win_rate_delta) * 100;
  const stdDev = parseFloat(card.std_win_rate) * 100;
  const winRate = parseFloat(card.avg_win_rate) * 100;
  const inclusionRate = parseFloat(card.inclusion_rate) * 100;

  const deltaClass = isNegative ? "text-[hsl(var(--knd-amber))]" : "text-primary";

  return (
    <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 p-2">
      <div className="flex-1 min-w-0">
        <a
          href={`https://scryfall.com/search?q=${encodeURIComponent(
            normalizeDisplayString(card.card_name)
          )}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-foreground hover:text-primary truncate block"
        >
          {normalizeDisplayString(card.card_name)}
        </a>
        <p className="text-xs text-muted-foreground">
          {card.deck_count} decks · {inclusionRate.toFixed(0)}% inclusion
        </p>
      </div>
      <div className="text-right ml-4">
        <div className="flex items-center gap-2 justify-end">
          <span className={`font-mono font-semibold ${deltaClass}`}>
            {delta > 0 ? "+" : ""}
            {delta.toFixed(1)}%
          </span>
          <span
            title="Two-sided p-value (normal approximation). Highlighted when p < 0.05."
            className={`rounded-full border px-2 py-0.5 text-[10px] ${
              (() => {
                const zScore = delta / (stdDev / Math.sqrt(card.deck_count));
                const pValue = 2 * (1 - normalCdf(Math.abs(zScore)));
                return pValue < 0.05
                  ? "border-primary/40 text-primary"
                  : "border-border/60 text-muted-foreground";
              })()
            }`}
          >
            {(() => {
              const zScore = delta / (stdDev / Math.sqrt(card.deck_count));
              const pValue = 2 * (1 - normalCdf(Math.abs(zScore)));
              return `p=${formatPValue(pValue)}`;
            })()}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          {winRate.toFixed(1)}% WR · ±{stdDev.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}

function RecentFinishRow({
  finish,
}: {
  finish: RecentFinish;
}) {
  const deckHost = (() => {
    if (!finish.decklist_url) return null;
    const url = finish.decklist_url.toLowerCase();
    if (url.includes("moxfield.com")) return "Moxfield";
    if (url.includes("topdeck.gg")) return "TopDeck";
    if (url.includes("archidekt.com")) return "Archidekt";
    return "Decklist";
  })();

  const tournamentUrl = finish.tournament.topdeck_tid
    ? `https://topdeck.gg/event/${finish.tournament.topdeck_tid}`
    : null;
  const playerDisplay = finish.player_name || finish.player_handle;
  const playerProfileUrl = finish.player_id ? `https://topdeck.gg/profile/${finish.player_id}` : null;
  const topdeckDeckUrl =
    finish.tournament.topdeck_tid && (finish.player_id || finish.player_handle)
      ? `https://topdeck.gg/deck/${finish.tournament.topdeck_tid}/${finish.player_id || finish.player_handle}`
      : null;
  const decklistHref = finish.decklist_url || topdeckDeckUrl;

  const dateLabel = new Date(finish.tournament.start_date).toLocaleDateString(
    "en-US",
    { month: "short", day: "numeric", year: "numeric" }
  );

  let medalLabel = finish.tournament.player_count <= 34 ? "Top 4" : "Top 16";
  let medalClass = "border-[hsl(var(--knd-amber))]/40 text-[hsl(var(--knd-amber))]";
  if (finish.final_standing === 1) {
    medalLabel = "1st";
    medalClass = "border-[hsl(var(--knd-amber))]/60 text-[hsl(var(--knd-amber))]";
  } else if (finish.made_top_cut) {
    medalLabel = "Top Cut";
    medalClass = "border-primary/40 text-primary";
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full border px-2 py-0.5 text-xs ${medalClass}`}>
            {medalLabel}
          </span>
          {tournamentUrl ? (
            <a
              href={tournamentUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-foreground truncate hover:text-primary"
            >
              {normalizeDisplayString(finish.tournament.name)}
            </a>
          ) : (
            <p className="text-sm font-medium text-foreground truncate">
              {normalizeDisplayString(finish.tournament.name)}
            </p>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {dateLabel} · {finish.tournament.player_count} players
          {finish.final_standing ? ` · Standing ${finish.final_standing}` : ""}
        </p>
        {playerDisplay ? (
          <p className="text-xs text-muted-foreground mt-1">
            Player{" "}
            {playerProfileUrl ? (
              <a
                href={playerProfileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground hover:text-primary"
              >
                {playerDisplay}
              </a>
            ) : (
              <span className="text-foreground">{playerDisplay}</span>
            )}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        {decklistHref ? (
          <a
            href={decklistHref}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-border/60 px-3 py-1 text-muted-foreground hover:border-primary/40 hover:text-foreground"
          >
            {deckHost || (topdeckDeckUrl ? "TopDeck" : "Decklist")}
          </a>
        ) : null}
      </div>
    </div>
  );
}
