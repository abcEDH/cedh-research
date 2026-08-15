import { Suspense } from "react";
import Link from "next/link";
import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import CommandersTable from "@/components/commanders/commanders-table";
import { getScryfallArtByNames } from "@/lib/commanders/fetchers";
import { splitCardName } from "@/lib/scryfall/client";
import CommanderTrendsTable, {
  CommanderPeriodSnapshot,
} from "@/components/commanders/commander-trends-table";
import CommanderTrendsChart, {
  CommanderTrendSeriesMeta,
  CommanderTrendSeriesPoint,
} from "@/components/commanders/commander-trends-chart";
import { formatPercent, mean } from "@/lib/commander-stats";
import { withTiming } from "@/lib/performance";

export const dynamic = "force-dynamic";
const COMMANDERS_CACHE_REVALIDATE_SECONDS = 60 * 60 * 24; // 24 hours

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

type CommanderUsageTrend = {
  data: CommanderTrendSeriesPoint[];
  series: CommanderTrendSeriesMeta[];
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
    .not("commander_name", "ilike", "unknown commander")
    .order("total_entries", { ascending: false });

  if (error) {
    console.error("Error fetching commanders:", error);
    throw error;
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

  let weeklyData: WeeklyTrendRow[] = weeklyPrimary.data ?? [];
  let monthlyData: MonthlyTrendRow[] = monthlyPrimary.data ?? [];

  if (weeklyPrimary.error) {
    console.error("Error fetching weekly trends (with players):", weeklyPrimary.error);
    const weeklyFallback = await supabase
      .from("commander_weekly_trends")
      .select("commander_id, week_start_date, entries, wins, losses, draws")
      .in("commander_id", commanderIds)
      .order("week_start_date", { ascending: true });
    if (weeklyFallback.error) {
      console.error("Error fetching weekly trends fallback:", weeklyFallback.error);
      throw weeklyFallback.error;
    }
    weeklyData = weeklyFallback.data ?? [];
  }

  if (monthlyPrimary.error) {
    console.error("Error fetching monthly trends (with players):", monthlyPrimary.error);
    const monthlyFallback = await supabase
      .from("commander_monthly_trends")
      .select("commander_id, month_key, entries, wins, losses, draws")
      .in("commander_id", commanderIds)
      .order("month_key", { ascending: true });
    if (monthlyFallback.error) {
      console.error("Error fetching monthly trends fallback:", monthlyFallback.error);
      throw monthlyFallback.error;
    }
    monthlyData = monthlyFallback.data ?? [];
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

async function getWeeklyEntries(commanderIds: string[], weeks = 104) {
  if (commanderIds.length === 0) return {};

  const { data, error } = await supabase
    .from("commander_weekly_trends")
    .select("commander_id, week_key, week_start_date, entries")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });

  if (error) {
    console.error("Error fetching weekly trends:", error);
    throw error;
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

async function getCommanderUsageTrend(commanderIds: string[]): Promise<CommanderUsageTrend> {
  if (commanderIds.length === 0) return { data: [], series: [] };

  const commanders = await getCachedCommanders();
  const commanderById = new Map(commanders.map((commander) => [commander.commander_id, commander]));
  const { data, error } = await supabase
    .from("commander_weekly_trends")
    .select("commander_id, week_key, week_start_date, entries")
    .in("commander_id", commanderIds)
    .order("week_start_date", { ascending: true });

  if (error) {
    console.error("Error fetching commander usage trends:", error);
    throw error;
  }

  const rows = (data ?? []) as WeeklyTrendRow[];
  const weekKeys = Array.from(
    new Set(rows.map((row) => normalizeDateKey(row.week_start_date) || row.week_key || "").filter(Boolean))
  ).sort().slice(-13);
  const entriesByWeek = new Map<string, Map<string, number>>();
  rows.forEach((row) => {
    const weekKey = normalizeDateKey(row.week_start_date) || row.week_key || "";
    if (!weekKey || !weekKeys.includes(weekKey)) return;
    const values = entriesByWeek.get(weekKey) ?? new Map<string, number>();
    values.set(row.commander_id, row.entries);
    entriesByWeek.set(weekKey, values);
  });

  return {
    data: weekKeys.map((week) => {
      const values = entriesByWeek.get(week);
      return Object.fromEntries([
        ["week", week],
        ...commanderIds.map((commanderId) => [commanderId, values?.get(commanderId) ?? null]),
      ]) as CommanderTrendSeriesPoint;
    }),
    series: commanderIds.flatMap((commanderId) => {
      const commander = commanderById.get(commanderId);
      return commander ? [{ id: commanderId, name: commander.commander_name }] : [];
    }),
  };
}

const getCachedCommanders = unstable_cache(
  () => withTiming("commanders:list", getCommanders),
  ["commanders-list-v1"],
  { revalidate: COMMANDERS_CACHE_REVALIDATE_SECONDS }
);

const getCachedCommanderPeriodSnapshots = unstable_cache(
  async (commanderIds: string[]) =>
    withTiming("commanders:period-snapshots", () => getCommanderPeriodSnapshots(commanderIds)),
  ["commander-period-snapshots-v1"],
  { revalidate: COMMANDERS_CACHE_REVALIDATE_SECONDS }
);

const getCachedWeeklyEntries = unstable_cache(
  async (commanderIds: string[], weeks: number) =>
    withTiming("commanders:weekly-entries", () => getWeeklyEntries(commanderIds, weeks)),
  ["commander-weekly-entries-v1"],
  { revalidate: COMMANDERS_CACHE_REVALIDATE_SECONDS }
);

const getCachedCommanderUsageTrend = unstable_cache(
  async (commanderIds: string[]) =>
    withTiming("commanders:usage-trend", () => getCommanderUsageTrend(commanderIds)),
  ["commander-usage-trend-v1"],
  { revalidate: COMMANDERS_CACHE_REVALIDATE_SECONDS }
);

export default function CommandersPage() {
  return (
    <div className="min-h-screen">
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <Link
              href="/"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              ← Back to Home
            </Link>
            <p className="mt-5 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Competitive Metagame
            </p>
            <h1 className="mt-1 text-3xl font-semibold text-foreground md:text-4xl">
              Commander Rankings
            </h1>
            <Suspense
              fallback={
                <p className="text-muted-foreground mt-2">
                  Loading commander rankings…
                </p>
              }
            >
              <CommanderHeaderSummary />
            </Suspense>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link
              href="/commanders/trends"
              className="min-h-11 rounded-full border border-border/60 px-3 py-2 text-muted-foreground hover:border-primary/40 hover:text-foreground"
            >
              View commander trends
            </Link>
          </div>
        </div>

        <Suspense fallback={<StatsSummarySkeleton />}>
          <StatsSummarySection />
        </Suspense>

        <div className="mb-8">
          <Suspense fallback={<SectionSkeleton label="Loading aggregate trends…" />}>
            <GlobalTrendsSection />
          </Suspense>
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
          <Suspense fallback={<SectionSkeleton label="Loading trends snapshot…" />}>
            <CommanderTrendsSection />
          </Suspense>
        </div>

        <Suspense fallback={<SectionSkeleton label="Loading commander rankings…" />}>
          <CommanderRankingsTable />
        </Suspense>
      </main>
    </div>
  );
}

async function CommanderHeaderSummary() {
  const commanders = await getCachedCommanders();
  return (
    <p className="text-muted-foreground mt-2">
      Performance data for {commanders.length} commanders with 5+ tournament entries.
    </p>
  );
}

async function StatsSummarySection() {
  const commanders = await getCachedCommanders();
  const totalEntries = commanders.reduce((sum, c) => sum + c.total_entries, 0);
  const avgWinRate = mean(commanders.map((c) => parseFloat(c.avg_win_rate)));
  const avgTop16 = mean(
    commanders.map((c) => parseFloat(c.conversion_rate_top_16))
  );

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-8">
      <StatCard
        label="Total Commanders"
        value={commanders.length.toString()}
        tone="neutral"
        tooltip="Number of commanders with 5+ entries."
        testId="stat-total-commanders"
      />
      <StatCard
        label="Total Entries"
        value={totalEntries.toLocaleString()}
        tone="neutral"
        tooltip="Total tournament entries across all listed commanders."
        testId="stat-total-entries"
      />
      <StatCard
        label="Avg Win Rate"
        value={formatPercent(avgWinRate)}
        tone="neutral"
        tooltip="Average commander win rate. Baseline in 4-player pods is 25%."
        testId="stat-avg-win-rate"
      />
      <StatCard
        label="Avg Top 16/Top 10/Top 4"
        value={formatPercent(avgTop16)}
        tone="neutral"
        tooltip="Average conversion into top bracket. Under 64 players, events may use Top 10, and for 34 players or fewer we only count Top 4 finishes."
      />
    </div>
  );
}

async function CommanderRankingsTable() {
  const commanders = await getCachedCommanders();
  const faceNames = Array.from(
    new Set(commanders.flatMap((c) => splitCardName(c.commander_name)))
  );
  const artByName = await getScryfallArtByNames(faceNames);
  return <CommandersTable commanders={commanders} artByName={artByName} />;
}

async function CommanderTrendsSection() {
  const commanders = await getCachedCommanders();
  const topCommanders = [...commanders]
    .sort((a, b) => b.total_entries - a.total_entries)
    .slice(0, 30);
  const topCommanderIds = topCommanders
    .map((commander) => commander.commander_id)
    .sort((a, b) => a.localeCompare(b));
  const [snapshotsByCommanderId, weeklyEntriesByCommanderId] = await Promise.all([
    getCachedCommanderPeriodSnapshots(topCommanderIds),
    getCachedWeeklyEntries(topCommanderIds, 12),
  ]);
  return (
    <CommanderTrendsTable
      commanders={topCommanders}
      snapshotsByCommanderId={snapshotsByCommanderId}
      weeklyEntriesByCommanderId={weeklyEntriesByCommanderId}
      limit={30}
    />
  );
}

async function GlobalTrendsSection() {
  const commanders = await getCachedCommanders();
  const commanderIds = commanders.slice(0, 10).map((commander) => commander.commander_id);
  const usageTrend = await getCachedCommanderUsageTrend(commanderIds);
  return (
    <CommanderTrendsChart
      data={usageTrend.data}
      series={usageTrend.series}
      yLabel="Entries"
      title="Most played commanders over time"
      description="Weekly tournament entries for the current top 10 commanders."
      valueFormatter={(value) => value.toLocaleString()}
      tickFormatter={(value) => value.toLocaleString()}
    />
  );
}

function StatsSummarySkeleton() {
  return (
    <div
      aria-hidden
      className="grid grid-cols-1 gap-4 md:grid-cols-4 mb-8"
    >
      {[0, 1, 2, 3].map((i) => (
        <Card key={i}>
          <CardContent className="pt-6">
            <div className="h-3 w-24 rounded bg-muted/40" />
            <div className="mt-3 h-7 w-20 rounded bg-muted/40" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div
      aria-hidden
      className="rounded-lg border border-border/40 bg-card/40 px-4 py-6 text-sm text-muted-foreground"
    >
      {label}
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
  tooltip,
  testId,
}: {
  label: string;
  value: string;
  tone: "primary" | "amber" | "neutral";
  tooltip?: string;
  testId?: string;
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
        <p data-testid={testId} className={`text-2xl font-semibold ${toneMap[tone]}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
