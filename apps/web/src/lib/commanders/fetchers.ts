import { supabase } from "@/lib/supabase";
import type { CommanderMatchup } from "@/components/commanders/commander-matchups-table";
import type { TrendMetricPoint, TrendMetricSeries } from "@/components/commanders/trend-metric-charts";

export interface CommanderStat {
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

export interface CommanderMeta {
  scryfall_ids: string[] | null;
  commander_names: string[] | null;
}

export interface CardReport {
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

export interface CardPerformance {
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

export interface NotablePlayer {
  player_name: string;
  topdeck_id: string | null;
  entries: number;
  total_wins: number;
  total_games: number;
  win_rate: string | null;
  top_16_count: number;
}

export interface RecentFinish {
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

export interface CommanderTrendTableRow {
  period: string;
  entries: number;
  winRate: number;
  pointsPerGame: number;
}

export interface MomentumPeriod {
  /** Human-readable label for the actual observed period, e.g. "Week of Aug 3, 2026" or "July 2026". */
  label: string;
  entries: number;
  /** Win rate (0-1) for this period. Always a real value: periods with zero recorded games are excluded upstream. */
  winRate: number;
  /** Percent change in entries vs. the prior comparable period, or null if there is no prior period to compare. */
  entriesChangePct: number | null;
  /** Percentage-point change in win rate vs. the prior comparable period, or null if there is no prior period. */
  winRateChangePp: number | null;
}

export interface CommanderMomentum {
  week: MomentumPeriod | null;
  month: MomentumPeriod | null;
}

function normalizeDateKey(value: string | null | undefined) {
  if (!value) return "";
  return value.length >= 10 ? value.slice(0, 10) : value;
}

export async function getCommanderDetails(id: string): Promise<CommanderStat | null> {
  const { data, error } = await supabase
    .from("commander_stats")
    .select("*")
    .eq("commander_id", id)
    .single();

  if (error || !data) return null;
  return data as CommanderStat;
}

export async function getCommanderMeta(id: string): Promise<CommanderMeta | null> {
  const { data, error } = await supabase
    .from("commanders")
    .select("scryfall_ids, commander_names")
    .eq("id", id)
    .single();

  if (error || !data) return null;
  return data as CommanderMeta;
}

export async function getRecentFinishes(commanderId: string, daysBack = 30): Promise<RecentFinish[]> {
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
      const tournament = Array.isArray(row.tournaments) ? row.tournaments[0] : row.tournaments;
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

  finishes.sort((a, b) => new Date(b.tournament.start_date).getTime() - new Date(a.tournament.start_date).getTime());

  const grouped = new Map<string, RecentFinish>();
  for (const finish of finishes) {
    const key = finish.decklist_url ?? finish.id;
    if (!grouped.has(key)) grouped.set(key, finish);
  }

  return Array.from(grouped.values()).slice(0, 20);
}

export async function getCardReport(commanderId: string): Promise<CardReport[]> {
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

export async function getCardPerformance(commanderId: string): Promise<CardPerformance[]> {
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

export async function getNotablePlayers(commanderId: string): Promise<NotablePlayer[]> {
  const { data, error } = await supabase.rpc("get_notable_players_for_commander", {
    p_commander_id: commanderId,
  });

  if (error) {
    console.error("Error fetching notable players:", error);
    return [];
  }
  return data as NotablePlayer[];
}

export async function getCommanderMatchups(commanderId: string): Promise<CommanderMatchup[]> {
  const { data, error } = await supabase.rpc("get_commander_matchups", {
    p_commander_id: commanderId,
  });

  if (error) {
    console.error("Error fetching matchups:", error);
    return [];
  }
  return data as CommanderMatchup[];
}

export async function getFirstPlaceFinishes(commanderId: string): Promise<number> {
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

interface MomentumSourceRow {
  entries: number;
  wins: number;
  losses: number;
  draws: number;
}

interface WeeklyMomentumRow extends MomentumSourceRow {
  week_start_date: string;
}

interface MonthlyMomentumRow extends MomentumSourceRow {
  month_key: string;
}

function formatWeekLabel(weekStartDate: string): string {
  const start = new Date(`${normalizeDateKey(weekStartDate)}T00:00:00Z`);
  return `Week of ${start.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })}`;
}

function formatMonthLabel(monthKey: string): string {
  const [year, month] = monthKey.split("-").map(Number);
  const start = new Date(Date.UTC(year, month - 1, 1));
  return start.toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" });
}

function isWeekComplete(weekStartDate: string, now: Date): boolean {
  const start = new Date(`${normalizeDateKey(weekStartDate)}T00:00:00Z`);
  const end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000);
  return end.getTime() <= now.getTime();
}

function isMonthComplete(monthKey: string, now: Date): boolean {
  const [year, month] = monthKey.split("-").map(Number);
  const nextMonthStart = new Date(Date.UTC(month === 12 ? year + 1 : year, month === 12 ? 0 : month, 1));
  return nextMonthStart.getTime() <= now.getTime();
}

/**
 * Picks the most recent *fully elapsed* observed period and the one before it.
 * Skips a still-in-progress period so an incomplete bucket is never compared
 * against a full prior bucket (which would look like a decline even when nothing declined).
 */
function pickCurrentAndPrevious<T extends MomentumSourceRow>(
  rowsDesc: T[],
  isComplete: (row: T) => boolean
): { current: T | null; previous: T | null } {
  const observed = rowsDesc.filter((row) => row.wins + row.losses + row.draws > 0);
  const startIndex = observed.length > 0 && !isComplete(observed[0]) ? 1 : 0;
  return { current: observed[startIndex] ?? null, previous: observed[startIndex + 1] ?? null };
}

function toMomentumPeriod<T extends MomentumSourceRow>(
  current: T,
  previous: T | null,
  label: string
): MomentumPeriod {
  const currentGames = current.wins + current.losses + current.draws;
  const winRate = current.wins / currentGames;

  let entriesChangePct: number | null = null;
  let winRateChangePp: number | null = null;

  if (previous) {
    const previousGames = previous.wins + previous.losses + previous.draws;
    if (previous.entries > 0) {
      entriesChangePct = ((current.entries - previous.entries) / previous.entries) * 100;
    }
    if (previousGames > 0) {
      winRateChangePp = (winRate - previous.wins / previousGames) * 100;
    }
  }

  return { label, entries: current.entries, winRate, entriesChangePct, winRateChangePp };
}

export async function getCommanderMomentum(commanderId: string): Promise<CommanderMomentum | null> {
  const now = new Date();

  const [weeklyResult, monthlyResult] = await Promise.all([
    supabase
      .from("commander_weekly_trends")
      .select("week_start_date, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .not("week_start_date", "is", null)
      .order("week_start_date", { ascending: false })
      .limit(8),
    supabase
      .from("commander_monthly_trends")
      .select("month_key, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .order("month_key", { ascending: false })
      .limit(8),
  ]);

  if (weeklyResult.error) console.error("Error fetching weekly momentum:", weeklyResult.error);
  if (monthlyResult.error) console.error("Error fetching monthly momentum:", monthlyResult.error);

  const weeklyRows = (weeklyResult.data || []) as WeeklyMomentumRow[];
  const monthlyRows = (monthlyResult.data || []) as MonthlyMomentumRow[];

  const { current: weekCurrent, previous: weekPrevious } = pickCurrentAndPrevious(weeklyRows, (row) =>
    isWeekComplete(row.week_start_date, now)
  );
  const { current: monthCurrent, previous: monthPrevious } = pickCurrentAndPrevious(monthlyRows, (row) =>
    isMonthComplete(row.month_key, now)
  );

  const week = weekCurrent ? toMomentumPeriod(weekCurrent, weekPrevious, formatWeekLabel(weekCurrent.week_start_date)) : null;
  const month = monthCurrent ? toMomentumPeriod(monthCurrent, monthPrevious, formatMonthLabel(monthCurrent.month_key)) : null;

  if (!week && !month) return null;
  return { week, month };
}

export type CommanderTrendSeries = TrendMetricSeries & {
  weeklyTable: CommanderTrendTableRow[];
  monthlyTable: CommanderTrendTableRow[];
};

export async function getCommanderTrendSeries(commanderId: string): Promise<CommanderTrendSeries> {
  const [weeklyResult, monthlyResult] = await Promise.all([
    supabase
      .from("commander_weekly_trends")
      .select("week_key, week_start_date, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .order("week_start_date", { ascending: true }),
    supabase
      .from("commander_monthly_trends")
      .select("month_key, entries, wins, losses, draws")
      .eq("commander_id", commanderId)
      .order("month_key", { ascending: true }),
  ]);

  if (weeklyResult.error) console.error("Error fetching commander weekly trends:", weeklyResult.error);
  if (monthlyResult.error) console.error("Error fetching commander monthly trends:", monthlyResult.error);

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

  function toMetricPoint(row: { entries: number; wins: number; losses: number; draws: number }, period: string): TrendMetricPoint {
    const games = row.wins + row.losses + row.draws;
    return {
      period,
      entries: row.entries,
      winRate: games ? (row.wins / games) * 100 : 0,
      pointsPerGame: games ? (row.wins * 5 + row.draws) / games : 0,
    };
  }

  const hasGames = (row: { wins: number; losses: number; draws: number }) =>
    row.wins + row.losses + row.draws > 0;

  const weekly: TrendMetricPoint[] = weeklyRows
    .filter(hasGames)
    .map((row) => toMetricPoint(row, normalizeDateKey(row.week_start_date) || row.week_key || ""));

  const monthly: TrendMetricPoint[] = monthlyRows
    .filter(hasGames)
    .map((row) => toMetricPoint(row, row.month_key));

  const weeklyTable: CommanderTrendTableRow[] = weeklyRows
    .filter(hasGames)
    .slice(-52)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      return {
        period: normalizeDateKey(row.week_start_date) || row.week_key || "",
        entries: row.entries,
        winRate: games ? (row.wins / games) * 100 : 0,
        pointsPerGame: games ? (row.wins * 5 + row.draws) / games : 0,
      };
    });

  const monthlyTable: CommanderTrendTableRow[] = monthlyRows
    .filter(hasGames)
    .slice(-52)
    .map((row) => {
      const games = row.wins + row.losses + row.draws;
      return {
        period: row.month_key,
        entries: row.entries,
        winRate: games ? (row.wins / games) * 100 : 0,
        pointsPerGame: games ? (row.wins * 5 + row.draws) / games : 0,
      };
    });

  return { weekly, monthly, weeklyTable, monthlyTable };
}
