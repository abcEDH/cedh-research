import type { MetaShareRow, PlayerCommanderProfile } from "@/lib/meta-prep";

export type PrecomputedCommanderPrediction = {
  commander: string;
  entries: number;
  prediction_score: number;
  prediction_share: number;
  model_share?: number | null;
  latest_date: string | null;
  latest_decklist_url: string | null;
};

export type PrecomputedCommanderProfileRow = {
  topdeck_id: string | null;
  player_name: string | null;
  total_entries: number;
  commander_predictions: PrecomputedCommanderPrediction[] | null;
};

export function buildProfilesFromPrecomputedRows(
  topdeckIds: string[],
  rows: PrecomputedCommanderProfileRow[]
): { players: PlayerCommanderProfile[]; metaShare: MetaShareRow[] } | null {
  const rowsByTopdeckId = new Map(
    rows.filter((row) => row.topdeck_id).map((row) => [row.topdeck_id as string, row])
  );
  if (rowsByTopdeckId.size === 0) return null;

  const metaTotals = new Map<string, number>();
  const players = topdeckIds.map((topdeckId) => {
    const row = rowsByTopdeckId.get(topdeckId);
    const commanders = (row?.commander_predictions ?? []).slice(0, 3).map((commander) => {
      const modelShare = commander.model_share ?? commander.prediction_share;
      metaTotals.set(
        commander.commander,
        (metaTotals.get(commander.commander) ?? 0) + modelShare
      );
      return {
        commander: commander.commander,
        entries: commander.entries,
        share: modelShare,
        weightedShare: modelShare,
        predictionShare: modelShare,
        predictionScore: commander.prediction_score,
        latestDate: commander.latest_date,
        latestDecklistUrl: commander.latest_decklist_url,
        latestTopdeckDecklistUrl: null,
      };
    });

    return {
      topdeckId,
      playerName: row?.player_name ?? "Unknown",
      totalEntries: row?.total_entries ?? 0,
      commanders,
    };
  });

  const totalMeta = Array.from(metaTotals.values()).reduce((sum, value) => sum + value, 0);
  const metaShare = Array.from(metaTotals.entries())
    .map(([commander, entries]) => ({
      commander,
      entries,
      share: totalMeta ? entries / totalMeta : 0,
    }))
    .sort((a, b) => b.entries - a.entries)
    .slice(0, 15);

  return { players, metaShare };
}
