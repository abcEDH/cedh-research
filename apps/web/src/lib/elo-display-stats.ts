import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";

export type EloDisplayStats = {
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

type EloDisplayTier = "ranking" | "all";
type EloDisplayStatsRecord = Record<string, EloDisplayStats>;

function emptyStats(): EloDisplayStats {
  return { games_played: 0, wins: 0, draws: 0, losses: 0 };
}

/**
 * Return display-only aggregates for ranking-eligible games.
 *
 * The Elo/rank values remain sourced from the leaderboard snapshot. This read
 * only changes the counters shown beside those values. The database function
 * starts from the displayed player IDs, rather than paging the much wider
 * game-results view through PostgREST.
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

  const { data, error } = await supabase.rpc("get_elo_display_stats", {
    p_topdeck_ids: uniqueTopdeckIds,
    p_tier: tier,
  });

  if (error) {
    console.error("Elo display stats RPC failed; retaining leaderboard counters:", error);
    // An empty map tells callers to retain the persisted counters already
    // returned by global_elo_active_leaderboard. Returning zero-valued entries
    // here would overwrite those valid aggregates during a migration rollout.
    return {};
  }

  for (const row of (data ?? []) as Array<{
    topdeck_id: string | null;
    games_played: number | null;
    wins: number | null;
    draws: number | null;
    losses: number | null;
  }>) {
    if (!row.topdeck_id || !statsByTopdeckId[row.topdeck_id]) continue;
    statsByTopdeckId[row.topdeck_id] = {
      games_played: row.games_played ?? 0,
      wins: row.wins ?? 0,
      draws: row.draws ?? 0,
      losses: row.losses ?? 0,
    };
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
