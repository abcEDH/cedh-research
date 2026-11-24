import { supabase } from "@/lib/supabase";
import type { WinrateMatrixRow, CommanderMetaEv } from "@/lib/schemas/api-contracts";

export type { WinrateMatrixRow, CommanderMetaEv };

export interface CommanderLabel {
  id: string;
  name: string;
}

export interface WinrateMatrixData {
  /** Top-N commanders ordered by metashare (games_played on their OVERALL row), descending. */
  commanderOrder: CommanderLabel[];
  rows: WinrateMatrixRow[];
  evByCommander: Map<string, CommanderMetaEv>;
}

const EMPTY_MATRIX: WinrateMatrixData = {
  commanderOrder: [],
  rows: [],
  evByCommander: new Map(),
};

/**
 * Fetches the top-N pairwise winrate matrix (#147) and the matching meta-EV column (#149) in
 * parallel, then resolves commander display names for the top-N set. The RPCs only return
 * ids -- see get_winrate_matrix/get_commander_meta_ev in
 * packages/backend/supabase/migrations/20261115000000_winrate_matrix_and_pod_metrics_rpc.sql
 * and .../20261115010000_commander_meta_ev_rpc.sql.
 */
export async function getWinrateMatrixData(daysBack: number, topN = 30): Promise<WinrateMatrixData> {
  const [matrixResult, evResult] = await Promise.all([
    supabase.rpc("get_winrate_matrix", { top_n: topN, days_back: daysBack }),
    supabase.rpc("get_commander_meta_ev", { top_n: topN, days_back: daysBack }),
  ]);

  if (matrixResult.error) {
    console.error("Error fetching winrate matrix:", matrixResult.error);
    return EMPTY_MATRIX;
  }

  const rows = (matrixResult.data ?? []) as WinrateMatrixRow[];
  const evRows = (evResult.data ?? []) as CommanderMetaEv[];
  if (evResult.error) {
    console.error("Error fetching commander meta EV (continuing without it):", evResult.error);
  }

  // The OVERALL row for each deck (deck_b_commander_id === null) carries its games_played
  // across the whole window, which is exactly the metashare ranking get_winrate_matrix already
  // used to decide the top-N cutoff -- no second RPC round trip needed to recover the order.
  const overallRows = rows
    .filter((row) => row.deck_b_commander_id === null)
    .sort((a, b) => b.games_played - a.games_played || a.deck_a_commander_id.localeCompare(b.deck_a_commander_id));

  const commanderIds = overallRows.map((row) => row.deck_a_commander_id);
  if (commanderIds.length === 0) {
    return EMPTY_MATRIX;
  }

  const { data: commanderRows, error: namesError } = await supabase
    .from("commanders")
    .select("id, name")
    .in("id", commanderIds);

  if (namesError) {
    console.error("Error fetching commander names for winrate matrix:", namesError);
  }

  const nameById = new Map((commanderRows ?? []).map((c: { id: string; name: string }) => [c.id, c.name]));
  const commanderOrder: CommanderLabel[] = commanderIds.map((id) => ({
    id,
    name: nameById.get(id) ?? "Unknown commander",
  }));

  const evByCommander = new Map(evRows.map((row) => [row.commander_id, row]));

  return { commanderOrder, rows, evByCommander };
}
