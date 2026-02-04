import "server-only";
import { supabase } from "@/lib/supabase";

export type CommanderUsageRow = {
  topdeck_id: string | null;
  player_name: string | null;
  commander_name: string | null;
  entries: number;
};

export type PlayerCommanderProfile = {
  topdeckId: string;
  playerName: string;
  totalEntries: number;
  commanders: Array<{ commander: string; entries: number; share: number }>;
};

export type MetaShareRow = {
  commander: string;
  entries: number;
  share: number;
};

export async function getCommanderUsageRows(
  topdeckIds: string[],
  lookbackStart: string
): Promise<CommanderUsageRow[]> {
  if (topdeckIds.length === 0) return [];

  const { data, error } = await supabase
    .from("player_commander_entries")
    .select("topdeck_id, player_name, commander_name, entries:count()")
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
  const perPlayer = new Map<string, CommanderUsageRow[]>();
  const commanderTotals = new Map<string, number>();

  usageRows.forEach((row) => {
    if (!row.topdeck_id || !row.commander_name) return;
    const list = perPlayer.get(row.topdeck_id) ?? [];
    list.push(row);
    perPlayer.set(row.topdeck_id, list);

    commanderTotals.set(
      row.commander_name,
      (commanderTotals.get(row.commander_name) ?? 0) + row.entries
    );
  });

  const totalEntries = Array.from(commanderTotals.values()).reduce((a, b) => a + b, 0);

  const players: PlayerCommanderProfile[] = topdeckIds.map((topdeckId) => {
    const rows = (perPlayer.get(topdeckId) ?? []).filter((row) => row.commander_name);
    const total = rows.reduce((sum, row) => sum + row.entries, 0);
    const sorted = rows.sort((a, b) => b.entries - a.entries);
    const commanders = sorted.slice(0, topN).map((row) => ({
      commander: row.commander_name || "Unknown",
      entries: row.entries,
      share: total ? row.entries / total : 0,
    }));

    return {
      topdeckId,
      playerName: rows[0]?.player_name || "Unknown",
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
