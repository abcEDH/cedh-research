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
    .map((row) => ({ ...toMetricPoint(row, normalizeDateKey(row.week_start_date) || row.week_key || "") }));

  const monthlyTable: CommanderTrendTableRow[] = monthlyRows
    .filter(hasGames)
    .slice(-52)
    .map((row) => ({ ...toMetricPoint(row, row.month_key) }));

  return { weekly, monthly, weeklyTable, monthlyTable };
}
