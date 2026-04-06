import "server-only";
import { supabase } from "@/lib/supabase";

export type CommanderUsageRow = {
  topdeck_id: string | null;
  player_name: string | null;
  commander_name: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  start_date: string | null;
};

export type PlayerCommanderProfile = {
  topdeckId: string;
  playerName: string;
  totalEntries: number;
  commanders: Array<{
    commander: string;
    entries: number;
    share: number;
    weightedShare: number;
    predictionShare: number;
    predictionScore: number;
    latestDate: string | null;
  }>;
};

export type MetaShareRow = {
  commander: string;
  entries: number;
  share: number;
};

function isKnownCommander(commanderName: string | null | undefined) {
  const normalized = (commanderName ?? "").trim().toLowerCase();
  return normalized.length > 0 && normalized !== "unknown commander";
}

export async function getCommanderUsageRows(
  topdeckIds: string[],
  lookbackStart: string
): Promise<CommanderUsageRow[]> {
  if (topdeckIds.length === 0) return [];

  const { data, error } = await supabase
    .from("player_commander_entries")
    .select("topdeck_id, player_name, commander_name, wins, draws, losses, start_date")
    .in("topdeck_id", topdeckIds)
    .gte("start_date", lookbackStart)
    .not("commander_name", "is", null);

  if (error) {
    throw new Error(`Error fetching commander usage: ${error.message}`);
  }

  return (data ?? []) as CommanderUsageRow[];
}

export function buildProfiles(
  topdeckIds: string[],
  usageRows: CommanderUsageRow[],
  topN = 3
): { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } {
  const perPlayer = new Map<
    string,
    Map<
      string,
      {
        entries: number;
        weightedPoints: number;
        predictionScore: number;
        latestDate: string | null;
        playerName: string;
      }
    >
  >();
  const playerNames = new Map<string, string>();
  const commanderTotals = new Map<string, number>();
  const latestTimestamp = usageRows.reduce((max, row) => {
    const timestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    return Number.isFinite(timestamp) ? Math.max(max, timestamp) : max;
  }, 0);

  usageRows.forEach((row) => {
    if (!row.topdeck_id || !isKnownCommander(row.commander_name)) return;
    const commanderName = row.commander_name as string;
    const playerName = row.player_name ?? "Unknown";
    if (row.player_name) {
      playerNames.set(row.topdeck_id, row.player_name);
    }
    const perCommander = perPlayer.get(row.topdeck_id) ?? new Map();
    const current = perCommander.get(commanderName) ?? {
      entries: 0,
      weightedPoints: 0,
      predictionScore: 0,
      latestDate: null,
      playerName,
    };
    const wins = row.wins ?? 0;
    const draws = row.draws ?? 0;
    const losses = row.losses ?? 0;
    const games = wins + draws + losses;
    const points = wins + draws * 0.25;
    const eventTimestamp = row.start_date ? new Date(row.start_date).getTime() : 0;
    const recencyWeight =
      latestTimestamp > 0 && eventTimestamp > 0
        ? Math.max(0.35, 1 - (latestTimestamp - eventTimestamp) / (1000 * 60 * 60 * 24 * 30 * 18))
        : 0.5;
    const efficiencyBoost = games > 0 ? 1 + points / games : 1;

    current.entries += 1;
    current.weightedPoints += points;
    current.predictionScore += recencyWeight * efficiencyBoost;
    if (!current.latestDate || (row.start_date && row.start_date > current.latestDate)) {
      current.latestDate = row.start_date;
    }
    perCommander.set(commanderName, current);
    perPlayer.set(row.topdeck_id, perCommander);

    commanderTotals.set(commanderName, (commanderTotals.get(commanderName) ?? 0) + 1);
  });

  const totalEntries = Array.from(commanderTotals.values()).reduce((a, b) => a + b, 0);

  const players: PlayerCommanderProfile[] = topdeckIds.map((topdeckId) => {
    const perCommander = perPlayer.get(topdeckId) ?? new Map();
    const rows = Array.from(perCommander.entries()).map(([commander, values]) => ({
      commander,
      entries: values.entries,
      weightedPoints: values.weightedPoints,
      predictionScore: values.predictionScore,
      latestDate: values.latestDate,
      playerName: values.playerName,
    }));
    const total = rows.reduce((sum, row) => sum + row.entries, 0);
    const totalWeighted = rows.reduce((sum, row) => sum + row.weightedPoints, 0);
    const totalPrediction = rows.reduce((sum, row) => sum + row.predictionScore, 0);
    const sorted = rows.sort((a, b) => {
      if (b.predictionScore !== a.predictionScore) return b.predictionScore - a.predictionScore;
      if (b.entries !== a.entries) return b.entries - a.entries;
      return b.weightedPoints - a.weightedPoints;
    });
    const commanders = sorted.slice(0, topN).map((row) => ({
      commander: row.commander,
      entries: row.entries,
      share: total ? row.entries / total : 0,
      weightedShare: totalWeighted ? row.weightedPoints / totalWeighted : total ? row.entries / total : 0,
      predictionShare: totalPrediction ? row.predictionScore / totalPrediction : total ? row.entries / total : 0,
      predictionScore: row.predictionScore,
      latestDate: row.latestDate,
    }));

    return {
      topdeckId,
      playerName: playerNames.get(topdeckId) || "Unknown",
      totalEntries: total,
      commanders,
    };
  });

  const metaShare: MetaShareRow[] = Array.from(commanderTotals.entries())
    .map(([commander, entries]) => ({
      commander,
      entries,
      share: totalEntries ? entries / totalEntries : 0,
    }))
    .sort((a, b) => b.entries - a.entries)
    .slice(0, 15);

  return { players, metaShare };
}

export function lookbackStartDate(months: number) {
  const start = new Date();
  start.setMonth(start.getMonth() - months);
  return start.toISOString().slice(0, 10);
}
