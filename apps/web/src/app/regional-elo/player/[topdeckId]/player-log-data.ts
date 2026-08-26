import "server-only";

import { supabase } from "@/lib/supabase";
import { withTiming } from "@/lib/performance";
import type { PlayerGameLog } from "./player-stats";

const PLAYER_GAME_LOG_LIMIT = 500;

export type PlayerRow = {
  id: string;
  name: string;
  topdeck_id: string;
};

type PlayerGameLogRpcRow = {
  game_id: string;
  game_date: string | null;
  tournament_name: string | null;
  state: string | null;
  round_number: number | null;
  round_name: string | null;
  table_number: number | null;
  seat_position: number | null;
  commander_name: string | null;
  game_result: string;
  tournament_player_count: number | null;
  ranking_eligible: boolean;
  opponents: PlayerGameLog["opponents"] | null;
};

function toRoundLabel(row: PlayerGameLogRpcRow) {
  if (row.round_name) return row.round_name;
  if (row.round_number !== null) return `Round ${row.round_number}`;
  return "Bracket";
}

export async function fetchPlayer(topdeckId: string): Promise<PlayerRow | null> {
  return withTiming("player-log-data:fetch-player", async () => {
    const { data } = await supabase
      .from("players")
      .select("id, name, topdeck_id")
      .eq("topdeck_id", topdeckId)
      .maybeSingle();

    return (data as PlayerRow | null) ?? null;
  });
}

export async function fetchRawPlayerLogs(playerId: string): Promise<PlayerGameLog[]> {
  return withTiming("player-log-data:paginated-rpc", async () => {
    const rows: PlayerGameLogRpcRow[] = [];

    for (let offset = 0; ; offset += PLAYER_GAME_LOG_LIMIT) {
      const { data, error } = await supabase.rpc("get_player_game_logs", {
        p_player_id: playerId,
        p_limit: PLAYER_GAME_LOG_LIMIT,
        p_offset: offset,
      });

      if (error) {
        throw new Error(`Error fetching player game log page: ${error.message}`);
      }

      const page = (data as PlayerGameLogRpcRow[] | null) ?? [];
      rows.push(...page);
      if (page.length < PLAYER_GAME_LOG_LIMIT) break;
    }

    return rows.map((row) => ({
      gameId: row.game_id,
      startDate: row.game_date ?? "",
      tournamentName: row.tournament_name ?? "Unknown tournament",
      state: row.state,
      roundLabel: toRoundLabel(row),
      tableLabel: row.table_number !== null ? `Table ${row.table_number}` : "Bracket",
      seat: (row.seat_position ?? 0) + 1,
      result: row.game_result,
      tournamentPlayerCount: row.tournament_player_count,
      rankingEligible: row.ranking_eligible,
      commanderName: row.commander_name,
      opponents: row.opponents ?? [],
    }));
  });
}

export async function fetchCanonicalPlayerLogs(
  playerId: string,
  regionFilter = ""
): Promise<PlayerGameLog[]> {
  const rows = await fetchRawPlayerLogs(playerId);
  if (!regionFilter) return rows;
  return rows.filter((row) => row.state?.toUpperCase() === regionFilter.toUpperCase());
}
