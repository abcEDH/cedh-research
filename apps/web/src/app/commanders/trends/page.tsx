import Link from "next/link";
import { supabase } from "@/lib/supabase";
import CommanderTrendsTable from "@/components/commanders/commander-trends-table";
import CommanderTrendsChart, {
  CommanderTrendSeriesPoint,
  CommanderTrendSeriesMeta,
} from "@/components/commanders/commander-trends-chart";
import TrendMetricCharts, {
  TrendMetricPoint,
  TrendMetricSeries,
} from "@/components/commanders/trend-metric-charts";
import type { CommanderPeriodSnapshot } from "@/components/commanders/commander-trends-table";

export const dynamic = "force-dynamic";
const SUPABASE_TREND_PAGE_SIZE = 1000;

type SizeFilter = "all" | "large";

function getTrendViews(sizeFilter: SizeFilter) {
  return {
    weekly: sizeFilter === "large" ? "commander_weekly_trends_large" : "commander_weekly_trends",
    monthly: sizeFilter === "large" ? "commander_monthly_trends_large" : "commander_monthly_trends",
    stats: sizeFilter === "large" ? "commander_stats_large" : "commander_stats",
  };
}

interface CommanderStat {
  commander_id: string;
  commander_name: string;
  total_entries: number;
  avg_win_rate: string;
}

type WeeklyTrendRow = {
  commander_id: string;
  week_key?: string | null;
  week_start_date?: string | null;
  entries: number;
  win_rate?: number;
  wins?: number | null;
  losses?: number | null;
  draws?: number | null;
  total_players?: number | null;
};

type MonthlyTrendRow = {
  commander_id: string;
  month_key?: string | null;
  entries: number;
  wins?: number | null;
  losses?: number | null;
  draws?: number | null;
  total_players?: number | null;
};

type GlobalWeeklyTrendRow = {
  week_key?: string | null;
  week_start_date?: string | null;
  entries: number;
  wins: number;
  losses: number;
  draws: number;
};

type GlobalMonthlyTrendRow = {
  month_key: string;
  entries: number;
  wins: number;
  losses: number;
  draws: number;
};

function normalizeDateKey(value: string | null | undefined) {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

async function getCommanders(sizeFilter: SizeFilter) {
  const { stats } = getTrendViews(sizeFilter);
  const { data, error } = await supabase
    .from(stats)
    .select("commander_id, commander_name, total_entries, avg_win_rate")
    .gt("total_entries", 5)
    .order("total_entries", { ascending: false });

  if (error) {
    console.error("Error fetching commanders:", error);
    return [];
  }
  return data as CommanderStat[];
}

async function getCommanderPeriodSnapshots(commanderIds: string[], sizeFilter: SizeFilter) {
  if (commanderIds.length === 0) return {};

  const { weekly, monthly } = getTrendViews(sizeFilter);
  const weeklyPrimary = await supabase
    .from(weekly)
    .select("commander_id, week_start_date, entries, wins, losses, draws, total_players")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });
  const monthlyPrimary = await supabase
    .from(monthly)
    .select("commander_id, month_key, entries, wins, losses, draws, total_players")
    .in("commander_id", commanderIds)
    .order("month_key", { ascending: true });

  let weeklyData: WeeklyTrendRow[] = weeklyPrimary.data ?? [];
  let monthlyData: MonthlyTrendRow[] = monthlyPrimary.data ?? [];

  if (weeklyPrimary.error) {
    console.error("Error fetching weekly trends (with players):", weeklyPrimary.error);
    const weeklyFallback = await supabase
      .from(weekly)
      .select("commander_id, week_start_date, entries, wins, losses, draws")
      .in("commander_id", commanderIds)
      .order("week_start_date", { ascending: true });
    weeklyData = weeklyFallback.data ?? [];
  }

  if (monthlyPrimary.error) {
    console.error("Error fetching monthly trends (with players):", monthlyPrimary.error);
    const monthlyFallback = await supabase
      .from(monthly)
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

  const weeklyRows = weeklyData;
  const monthlyRows = monthlyData;

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
    const weekWins = week?.wins ?? 0;
    const weekLosses = week?.losses ?? 0;
    const weekDraws = week?.draws ?? 0;
    const monthWins = month?.wins ?? 0;
    const monthLosses = month?.losses ?? 0;
    const monthDraws = month?.draws ?? 0;
    const weekGames = week ? weekWins + weekLosses + weekDraws : 0;
    const monthGames = month ? monthWins + monthLosses + monthDraws : 0;

    snapshots[commanderId] = {
      weekStart: week?.week_start_date ?? null,
      weekEntries: week?.entries ?? null,
      weekWinRate: weekGames ? (weekWins / weekGames) * 100 : null,
      weekPointsPerGame: weekGames ? (weekWins * 5 + weekDraws) / weekGames : null,
      weekPlayers: week?.total_players ?? null,
      monthKey: month?.month_key ?? null,
      monthEntries: month?.entries ?? null,
      monthWinRate: monthGames ? (monthWins / monthGames) * 100 : null,
      monthPointsPerGame: monthGames ? (monthWins * 5 + monthDraws) / monthGames : null,
      monthPlayers: month?.total_players ?? null,
    };
  });

  return snapshots;
}

async function getWeeklyEntries(commanderIds: string[], sizeFilter: SizeFilter, weeks = 104) {
  if (commanderIds.length === 0) return {};

  const { weekly } = getTrendViews(sizeFilter);
  const { data, error } = await supabase
    .from(weekly)
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
      const aKey = a.week_start_date || a.week_key || "";
      const bKey = b.week_start_date || b.week_key || "";
      return aKey.localeCompare(bKey);
    });
    const values = sorted.slice(-weeks).map((row) => row.entries);
    result[commanderId] = values;
  });

  return result;
}

async function getWeeklyWinRateSeries(commanders: CommanderStat[], sizeFilter: SizeFilter, weeks = 104) {
  if (commanders.length === 0) {
    return { data: [] as CommanderTrendSeriesPoint[], series: [] as CommanderTrendSeriesMeta[] };
  }

  const { weekly } = getTrendViews(sizeFilter);
  const commanderIds = commanders.map((commander) => commander.commander_id);
  const { data, error } = await supabase
    .from(weekly)
    .select("commander_id, week_key, week_start_date, win_rate")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });

  if (error) {
    console.error("Error fetching weekly win rate trends:", error);
    return { data: [], series: [] };
  }

  const rows = (data || []) as WeeklyTrendRow[];
  const grouped = new Map<string, WeeklyTrendRow[]>();
  rows.forEach((row) => {
    const list = grouped.get(row.commander_id) ?? [];
    list.push(row);
    grouped.set(row.commander_id, list);
  });

  const weekKeys = Array.from(
    new Set(rows.map((row) => normalizeDateKey(row.week_start_date) || row.week_key || ""))
  )
    .filter(Boolean)
    .sort((a, b) => Date.parse(a) - Date.parse(b));
  const slicedWeekKeys = weekKeys.slice(-weeks);

  const dataPoints: CommanderTrendSeriesPoint[] = slicedWeekKeys.map((week) => ({ week }));
  grouped.forEach((rowsForCommander, commanderId) => {
    const map = new Map(
      rowsForCommander.map((row) => [normalizeDateKey(row.week_start_date) || row.week_key || "", row.win_rate ?? null])
    );
    dataPoints.forEach((point) => {
      const value = map.get(point.week) ?? null;
      point[commanderId] = value !== null && value !== undefined ? Math.round(value * 1000) / 10 : null;
    });
  });

  const series: CommanderTrendSeriesMeta[] = commanders.map((commander) => ({
    id: commander.commander_id,
    name: commander.commander_name,
  }));

  return { data: dataPoints, series };
}

async function fetchGlobalWeeklyTrendRows(weeklyView: string) {
  const rows: GlobalWeeklyTrendRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_TREND_PAGE_SIZE) {
    const { data, error } = await supabase
      .from(weeklyView)
      .select("week_key, week_start_date, entries, wins, losses, draws")
      .order("week_start_date", { ascending: true })
      .range(offset, offset + SUPABASE_TREND_PAGE_SIZE - 1);

    if (error) {
      console.error("Error fetching global weekly trends:", error);
      return rows;
    }

    rows.push(...(((data as GlobalWeeklyTrendRow[]) ?? [])));
    if (!data || data.length < SUPABASE_TREND_PAGE_SIZE) break;
  }
  return rows;
}

async function fetchGlobalMonthlyTrendRows(monthlyView: string) {
  const rows: GlobalMonthlyTrendRow[] = [];
  for (let offset = 0; ; offset += SUPABASE_TREND_PAGE_SIZE) {
    const { data, error } = await supabase
      .from(monthlyView)
      .select("month_key, entries, wins, losses, draws")
      .order("month_key", { ascending: true })
      .range(offset, offset + SUPABASE_TREND_PAGE_SIZE - 1);

    if (error) {
      console.error("Error fetching global monthly trends:", error);
      return rows;
    }

    rows.push(...(((data as GlobalMonthlyTrendRow[]) ?? [])));
    if (!data || data.length < SUPABASE_TREND_PAGE_SIZE) break;
  }
  return rows;
}

async function getGlobalTrendSeries(sizeFilter: SizeFilter) {
  const { weekly: weeklyView, monthly: monthlyView } = getTrendViews(sizeFilter);
  const [weeklyRows, monthlyRows] = await Promise.all([
    fetchGlobalWeeklyTrendRows(weeklyView),
    fetchGlobalMonthlyTrendRows(monthlyView),
  ]);

  const weeklyByKey = new Map<string, { entries: number; wins: number; losses: number; draws: number }>();
  weeklyRows.forEach((row) => {
    const key = row.week_start_date || row.week_key;
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

export default async function CommanderTrendsPage({
  searchParams,
}: {
  searchParams?: Promise<{ size?: string | string[] }> | { size?: string | string[] };
}) {
  const resolvedSearchParams = await searchParams;
  const rawSize = Array.isArray(resolvedSearchParams?.size)
    ? resolvedSearchParams?.size[0]
    : resolvedSearchParams?.size;
  const sizeFilter: SizeFilter = rawSize === "large" ? "large" : "all";
  const sizeLabel = sizeFilter === "large" ? "65+ players" : "32+ players";

  const commanders = await getCommanders(sizeFilter);
  const filteredCommanders = commanders.filter(
    (commander) => commander.commander_name?.toLowerCase() !== "unknown commander"
  );
  const topCommanders = [...filteredCommanders].sort((a, b) => b.total_entries - a.total_entries).slice(0, 10);
  const snapshotsByCommanderId = await getCommanderPeriodSnapshots(
    filteredCommanders.map((commander) => commander.commander_id),
    sizeFilter
  );
  const weeklyEntriesByCommanderId = await getWeeklyEntries(
    filteredCommanders.map((commander) => commander.commander_id),
    sizeFilter,
    12
  );
  const { data: chartData, series: chartSeries } = await getWeeklyWinRateSeries(
    topCommanders,
    sizeFilter,
    13
  );
  const globalSeries = await getGlobalTrendSeries(sizeFilter);

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
            <h1 className="mt-4 text-3xl font-semibold text-foreground md:text-4xl">
              Commander Trends
            </h1>
            <p className="text-muted-foreground mt-2">
              Week-over-week and month-over-month changes based on tournament entries and win rates.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <Link
                href="/commanders/trends"
                className={`rounded-full border px-3 py-1 ${
                  sizeFilter === "all"
                    ? "border-primary/50 text-foreground"
                    : "border-border/60 text-muted-foreground"
                }`}
              >
                32+ Players
              </Link>
              <Link
                href="/commanders/trends?size=large"
                className={`rounded-full border px-3 py-1 ${
                  sizeFilter === "large"
                    ? "border-primary/50 text-foreground"
                    : "border-border/60 text-muted-foreground"
                }`}
              >
                65+ Players
              </Link>
            </div>
          </div>
        </div>

        <TrendMetricCharts
          series={globalSeries}
          title={`All commanders (${sizeLabel})`}
          description="Aggregate trends across all commanders (entries, win rate, points per game)."
        />

        <div className="mt-8">
          <CommanderTrendsChart
            data={chartData}
            series={chartSeries}
            title={`Top 10 commanders over time (${sizeLabel})`}
            description="Weekly win rate trends (last 13 weeks)."
          />
        </div>

        <div className="mt-8">
          <CommanderTrendsTable
            commanders={filteredCommanders}
            snapshotsByCommanderId={snapshotsByCommanderId}
            weeklyEntriesByCommanderId={weeklyEntriesByCommanderId}
            limit={100}
            title={`Commander Performance Trends (${sizeLabel})`}
          />
        </div>
      </main>
    </div>
  );
}
