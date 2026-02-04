import "server-only";
import { supabase } from "@/lib/supabase";

export type CommanderUsageRow = {
  topdeck_id: string | null;
  player_name: string | null;
  commander_name: string | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
};

export type PlayerCommanderProfile = {
  topdeckId: string;
  playerName: string;
  totalEntries: number;
  commanders: Array<{ commander: string; entries: number; share: number; weightedShare: number }>;
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
    .select("topdeck_id, player_name, commander_name, wins, draws, losses")
    .in("topdeck_id", topdeckIds)
    .gte("start_date", lookbackStart)
    .not("commander_name", "is", null);

  if (error) {
    console.error("Error fetching commander usage:", error);
    return [];
  }

  return (data ?? []) as CommanderUsageRow[];
}

export function buildProfiles(
  topdeckIds: string[],
  usageRows: CommanderUsageRow[],
  topN = 3
): { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } {
  const perPlayer = new Map<string, Map<string, { entries: number; weightedPoints: number; playerName: string }>>();
  const commanderTotals = new Map<string, number>();

  usageRows.forEach((row) => {
    if (!row.topdeck_id || !isKnownCommander(row.commander_name)) return;
    const commanderName = row.commander_name as string;
    const playerName = row.player_name ?? "Unknown";
    const perCommander = perPlayer.get(row.topdeck_id) ?? new Map();
    const current = perCommander.get(commanderName) ?? {
      entries: 0,
      weightedPoints: 0,
      playerName,
    };
    current.entries += 1;
    current.weightedPoints += (row.wins ?? 0) + (row.draws ?? 0) * 0.25;
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
      playerName: values.playerName,
    }));
    const total = rows.reduce((sum, row) => sum + row.entries, 0);
    const totalWeighted = rows.reduce((sum, row) => sum + row.weightedPoints, 0);
    const sorted = rows.sort((a, b) => b.entries - a.entries);
    const commanders = sorted.slice(0, topN).map((row) => ({
      commander: row.commander,
      entries: row.entries,
      share: total ? row.entries / total : 0,
      weightedShare: totalWeighted ? row.weightedPoints / totalWeighted : total ? row.entries / total : 0,
    }));

    return {
      topdeckId,
      playerName: rows[0]?.playerName || "Unknown",
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
