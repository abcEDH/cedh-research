import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import CommandersTable from "@/components/commanders/commanders-table";
import CommanderTrendsTable, {
  CommanderPeriodSnapshot,
} from "@/components/commanders/commander-trends-table";
import TrendMetricCharts, {
  TrendMetricPoint,
  TrendMetricSeries,
} from "@/components/commanders/trend-metric-charts";

export const dynamic = "force-dynamic";

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

type WeeklyTrendRow = {
  commander_id: string;
  week_key?: string | null;
  week_start_date?: string | null;
  entries: number;
};

function normalizeDateKey(value: string | null | undefined) {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

async function getCommanders() {
  const { data, error } = await supabase
    .from("commander_stats")
    .select("*")
    .gt("total_entries", 5)
    .order("total_entries", { ascending: false });

  if (error) {
    console.error("Error fetching commanders:", error);
    return [];
  }
  return data as CommanderStat[];
}

async function getCommanderPeriodSnapshots(commanderIds: string[]) {
  if (commanderIds.length === 0) return {};

  const weeklyPrimary = await supabase
    .from("commander_weekly_trends")
    .select("commander_id, week_start_date, entries, wins, losses, draws, total_players")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });
  const monthlyPrimary = await supabase
    .from("commander_monthly_trends")
    .select("commander_id, month_key, entries, wins, losses, draws, total_players")
    .in("commander_id", commanderIds)
    .order("month_key", { ascending: true });

  let weeklyData: any[] = weeklyPrimary.data ?? [];
  let monthlyData: any[] = monthlyPrimary.data ?? [];

  if (weeklyPrimary.error) {
    console.error("Error fetching weekly trends (with players):", weeklyPrimary.error);
    const weeklyFallback = await supabase
      .from("commander_weekly_trends")
      .select("commander_id, week_start_date, entries, wins, losses, draws")
      .in("commander_id", commanderIds)
      .order("week_start_date", { ascending: true });
    weeklyData = weeklyFallback.data ?? [];
  }

  if (monthlyPrimary.error) {
    console.error("Error fetching monthly trends (with players):", monthlyPrimary.error);
    const monthlyFallback = await supabase
      .from("commander_monthly_trends")
      .select("commander_id, month_key, entries, wins, losses, draws")
      .in("commander_id", commanderIds)
      .order("month_key", { ascending: true });
    monthlyData = monthlyFallback.data ?? [];
  }

  if (weeklyPrimary.error) {
    console.error("Error fetching weekly trends:", weeklyPrimary.error);
  }
  if (monthlyPrimary.error) {
    console.error("Error fetching monthly trends:", monthlyPrimary.error);
  }

  const weeklyRows = (weeklyData || []) as {
    commander_id: string;
    week_start_date: string;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
    total_players?: number | null;
  }[];
  const monthlyRows = (monthlyData || []) as {
    commander_id: string;
    month_key: string;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
    total_players?: number | null;
  }[];

  const weeklyLatest = new Map<string, typeof weeklyRows[number]>();
  weeklyRows.forEach((row) => {
    weeklyLatest.set(row.commander_id, row);
  });

  const monthlyLatest = new Map<string, typeof monthlyRows[number]>();
  monthlyRows.forEach((row) => {
    monthlyLatest.set(row.commander_id, row);
  });

  const snapshots: Record<string, CommanderPeriodSnapshot> = {};
  commanderIds.forEach((commanderId) => {
    const week = weeklyLatest.get(commanderId);
    const month = monthlyLatest.get(commanderId);
    const weekGames = week ? week.wins + week.losses + week.draws : 0;
    const monthGames = month ? month.wins + month.losses + month.draws : 0;

    snapshots[commanderId] = {
      weekStart: week?.week_start_date ?? null,
      weekEntries: week?.entries ?? null,
      weekWinRate: weekGames ? (week!.wins / weekGames) * 100 : null,
      weekPointsPerGame: weekGames ? (week!.wins * 5 + week!.draws) / weekGames : null,
      weekPlayers: week?.total_players ?? null,
      monthKey: month?.month_key ?? null,
      monthEntries: month?.entries ?? null,
      monthWinRate: monthGames ? (month!.wins / monthGames) * 100 : null,
      monthPointsPerGame: monthGames ? (month!.wins * 5 + month!.draws) / monthGames : null,
      monthPlayers: month?.total_players ?? null,
    };
  });

  return snapshots;
}

async function getWeeklyEntries(commanderIds: string[], weeks = 12) {
  if (commanderIds.length === 0) return {};

  const { data, error } = await supabase
    .from("commander_weekly_trends")
    .select("commander_id, week_key, week_start_date, entries")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });

  if (error) {
    console.error("Error fetching weekly trends:", error);
    return {};
  }

  const rows = (data || []) as WeeklyTrendRow[];
  const grouped = new Map<string, WeeklyTrendRow[]>();
  rows.forEach((row) => {
    const list = grouped.get(row.commander_id) ?? [];
    list.push(row);
    grouped.set(row.commander_id, list);
  });

  const result: Record<string, number[]> = {};
  grouped.forEach((rowsForCommander, commanderId) => {
    const sorted = rowsForCommander.sort((a, b) => {
      const aKey = normalizeDateKey(a.week_start_date) || a.week_key || "";
      const bKey = normalizeDateKey(b.week_start_date) || b.week_key || "";
      return aKey.localeCompare(bKey);
    });
    const values = sorted.slice(-weeks).map((row) => row.entries);
    result[commanderId] = values;
  });

  return result;
}

async function getGlobalTrendSeries() {
  const [weeklyResult, monthlyResult] = await Promise.all([
    supabase
      .from("commander_weekly_trends")
      .select("week_key, week_start_date, entries, wins, losses, draws")
      .order("week_start_date", { ascending: true }),
    supabase
      .from("commander_monthly_trends")
      .select("month_key, entries, wins, losses, draws")
      .order("month_key", { ascending: true }),
  ]);

  if (weeklyResult.error) {
    console.error("Error fetching global weekly trends:", weeklyResult.error);
  }
  if (monthlyResult.error) {
    console.error("Error fetching global monthly trends:", monthlyResult.error);
  }

  const weeklyRows = (weeklyResult.data || []) as {
    week_key?: string | null;
    week_start_date?: string | null;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
  }[];
  const monthlyRows = (monthlyResult.data || []) as {
    month_key: string;
    entries: number;
    wins: number;
    losses: number;
    draws: number;
  }[];

  const weeklyByKey = new Map<string, { entries: number; wins: number; losses: number; draws: number }>();
  weeklyRows.forEach((row) => {
    const key = normalizeDateKey(row.week_start_date) || row.week_key;
    if (!key) return;
    const current = weeklyByKey.get(key) ?? { entries: 0, wins: 0, losses: 0, draws: 0 };
    current.entries += row.entries ?? 0;
    current.wins += row.wins ?? 0;
    current.losses += row.losses ?? 0;
    current.draws += row.draws ?? 0;
    weeklyByKey.set(key, current);
  });

  const monthlyByKey = new Map<string, { entries: number; wins: number; losses: number; draws: number }>();
  monthlyRows.forEach((row) => {
    const current = monthlyByKey.get(row.month_key) ?? { entries: 0, wins: 0, losses: 0, draws: 0 };
    current.entries += row.entries ?? 0;
    current.wins += row.wins ?? 0;
    current.losses += row.losses ?? 0;
    current.draws += row.draws ?? 0;
    monthlyByKey.set(row.month_key, current);
  });

  const weekly: TrendMetricPoint[] = Array.from(weeklyByKey.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-26)
    .map(([period, values]) => {
      const games = values.wins + values.losses + values.draws;
      const winRate = games ? (values.wins / games) * 100 : 0;
      const pointsPerGame = games ? (values.wins * 5 + values.draws) / games : 0;
      return { period, entries: values.entries, winRate, pointsPerGame };
    });

  const monthly: TrendMetricPoint[] = Array.from(monthlyByKey.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-18)
    .map(([period, values]) => {
      const games = values.wins + values.losses + values.draws;
      const winRate = games ? (values.wins / games) * 100 : 0;
      const pointsPerGame = games ? (values.wins * 5 + values.draws) / games : 0;
      return { period, entries: values.entries, winRate, pointsPerGame };
    });

  return { weekly, monthly } satisfies TrendMetricSeries;
}

export default async function CommandersPage() {
  const commanders = await getCommanders();
  const filteredCommanders = commanders.filter(
    (commander) => commander.commander_name?.toLowerCase() !== "unknown commander"
  );
  const topCommanders = [...filteredCommanders].sort((a, b) => b.total_entries - a.total_entries).slice(0, 30);
  const snapshotsByCommanderId = await getCommanderPeriodSnapshots(
    topCommanders.map((commander) => commander.commander_id)
  );
  const weeklyEntriesByCommanderId = await getWeeklyEntries(
    topCommanders.map((commander) => commander.commander_id),
    12
  );
  const globalSeries = await getGlobalTrendSeries();

  const totalEntries = filteredCommanders.reduce((sum, c) => sum + c.total_entries, 0);
  const avgWinRate =
    filteredCommanders.reduce((sum, c) => sum + parseFloat(c.avg_win_rate), 0) /
    Math.max(filteredCommanders.length, 1);
  const avgTop16 =
    filteredCommanders.reduce((sum, c) => sum + parseFloat(c.conversion_rate_top_16), 0) /
    Math.max(filteredCommanders.length, 1);

  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="relative mb-8 overflow-hidden rounded-2xl border border-border/70 bg-card/60 px-6 py-6">
          <div className="knd-watermark absolute inset-0" />
          <div className="relative">
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Home
            </Link>
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Commander Rankings
            </h1>
            <p className="text-muted-foreground mt-2">
              Performance data for {filteredCommanders.length} commanders with 5+ tournament entries.
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-sm">
              <Link
                href="/commanders/trends"
                className="rounded-full border border-border/60 px-3 py-1 text-muted-foreground hover:border-primary/40 hover:text-foreground"
              >
                View commander trends
              </Link>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-8">
          <StatCard
            label="Total Commanders"
            value={filteredCommanders.length.toString()}
            tone="neutral"
            tooltip="Number of commanders with 5+ entries."
          />
          <StatCard
            label="Total Entries"
            value={totalEntries.toLocaleString()}
            tone="neutral"
            tooltip="Total tournament entries across all listed commanders."
          />
          <StatCard
            label="Avg Win Rate"
            value={`${(avgWinRate * 100).toFixed(1)}%`}
            tone="neutral"
            tooltip="Average commander win rate. Baseline in 4-player pods is 25%."
          />
          <StatCard
            label="Avg Top 16/Top 10"
            value={`${(avgTop16 * 100).toFixed(1)}%`}
            tone="neutral"
            tooltip="Average conversion into top bracket. Under 64 players, events may use Top 10 instead of Top 16."
          />
        </div>

        <div className="mb-8">
          <TrendMetricCharts
            series={globalSeries}
            title="All commanders"
            description="Aggregate trends across all commanders (entries, win rate, points per game)."
          />
        </div>

        <div className="mb-8">
          <div className="mb-3 flex items-center justify-between text-sm">
            <p className="text-muted-foreground">
              Trending snapshot for the most played commanders.
            </p>
            <Link
              href="/commanders/trends"
              className="text-muted-foreground hover:text-foreground"
            >
              Explore full trends →
            </Link>
          </div>
          <CommanderTrendsTable
            commanders={topCommanders}
            snapshotsByCommanderId={snapshotsByCommanderId}
            weeklyEntriesByCommanderId={weeklyEntriesByCommanderId}
            limit={30}
          />
        </div>

        <CommandersTable commanders={filteredCommanders} />
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
      <CardContent className="pt-6">
        <div className="flex items-center gap-2">
          <p className="text-muted-foreground text-sm uppercase tracking-[0.2em]">{label}</p>
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
        <p className={`text-2xl font-semibold ${toneMap[tone]}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
