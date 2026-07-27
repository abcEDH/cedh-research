import { supabase } from "@/lib/supabase";

export type EloDisplayStats = {
  games_played: number;
  wins: number;
  draws: number;
  losses: number;
};

const PLAYER_ID_BATCH_SIZE = 50;
const GAME_PAGE_SIZE = 1000;

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
export async function fetchEloDisplayStats(
  topdeckIds: string[]
): Promise<Map<string, EloDisplayStats>> {
  const uniqueTopdeckIds = Array.from(new Set(topdeckIds.filter(Boolean)));
  const statsByTopdeckId = new Map<string, EloDisplayStats>();

  for (const topdeckId of uniqueTopdeckIds) {
    statsByTopdeckId.set(topdeckId, emptyStats());
  }

  for (let batchStart = 0; batchStart < uniqueTopdeckIds.length; batchStart += PLAYER_ID_BATCH_SIZE) {
    const batch = uniqueTopdeckIds.slice(batchStart, batchStart + PLAYER_ID_BATCH_SIZE);

    for (let pageStart = 0; ; pageStart += GAME_PAGE_SIZE) {
      const { data, error } = await supabase
        .from("global_elo_game_results")
        .select("game_id, topdeck_id, result")
        .in("topdeck_id", batch)
        .eq("ranking_eligible", true)
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
        const stats = statsByTopdeckId.get(row.topdeck_id);
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
