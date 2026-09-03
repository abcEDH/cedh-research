import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";

export type EloDisplayStats = {
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

const PLAYER_ID_BATCH_SIZE = 50;
const GAME_PAGE_SIZE = 1000;
type EloDisplayTier = "ranking" | "all";
type EloDisplayStatsRecord = Record<string, EloDisplayStats>;

function emptyStats(): EloDisplayStats {
  return { games_played: 0, wins: 0, draws: 0, losses: 0 };
}

/**
 * Return display-only aggregates for ranking-eligible games.
 *
 * The Elo/rank values remain sourced from the leaderboard snapshot. This read
 * only changes the counters shown beside those values and deliberately pages
 * through the game-level view so long player histories are complete.
 */
async function fetchEloDisplayStatsInner(
  topdeckIds: string[],
  tier: EloDisplayTier = "ranking"
): Promise<EloDisplayStatsRecord> {
  const uniqueTopdeckIds = Array.from(new Set(topdeckIds.filter(Boolean)));
  const statsByTopdeckId: EloDisplayStatsRecord = {};

  for (const topdeckId of uniqueTopdeckIds) {
    statsByTopdeckId[topdeckId] = emptyStats();
  }

  for (let batchStart = 0; batchStart < uniqueTopdeckIds.length; batchStart += PLAYER_ID_BATCH_SIZE) {
    const batch = uniqueTopdeckIds.slice(batchStart, batchStart + PLAYER_ID_BATCH_SIZE);
    const eligibilityColumn = tier === "ranking" ? "ranking_eligible" : "all_eligible";

    for (let pageStart = 0; ; pageStart += GAME_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("global_elo_game_results")
        .select("game_id, topdeck_id, result")
        .in("topdeck_id", batch)
        .eq(eligibilityColumn, true)
        .order("game_id", { ascending: true })
        .range(pageStart, pageStart + GAME_PAGE_SIZE - 1);

      if (error) {
        throw new Error(`Elo display stats query failed: ${error.message}`);
      }

      const rows = (data ?? []) as Array<{
        topdeck_id: string | null;
        result: string | null;
      }>;

      for (const row of rows) {
        if (!row.topdeck_id) continue;
        const stats = statsByTopdeckId[row.topdeck_id];
        if (!stats) continue;

        if (row.result === "win") stats.wins += 1;
        else if (row.result === "draw") stats.draws += 1;
        else if (row.result === "loss") stats.losses += 1;
        else continue;

        stats.games_played += 1;
      }

      if (rows.length < GAME_PAGE_SIZE) break;
    }
  }

  return statsByTopdeckId;
}

const getCachedEloDisplayStatsInner = unstable_cache(
  fetchEloDisplayStatsInner,
  ["elo-display-stats-v1"],
  { revalidate: 60 * 60 * 24 }
);

/**
 * Cached wrapper over the inner query. Sorts + deduplicates player IDs so the
 * cache key is stable regardless of caller order, and round-trips through a
 * plain object because `unstable_cache` serialises to JSON (killing the Map).
 */
export async function fetchEloDisplayStats(
  topdeckIds: string[],
  tier: EloDisplayTier = "ranking"
): Promise<Map<string, EloDisplayStats>> {
  const stableIds = Array.from(new Set(topdeckIds.filter(Boolean))).sort();
  const cached = await getCachedEloDisplayStatsInner(stableIds, tier);
  return new Map(Object.entries(cached));
}
