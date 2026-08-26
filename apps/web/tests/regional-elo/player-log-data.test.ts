import { beforeEach, describe, expect, it, vi } from "vitest";

const rpc = vi.fn();

vi.mock("@/lib/supabase", () => ({
  supabase: { rpc },
}));

vi.mock("@/lib/performance", () => ({
  withTiming: (_label: string, operation: () => unknown) => operation(),
}));

function rpcRow(index: number) {
  return {
    game_id: `game-${index}`,
    game_date: "2026-01-01T00:00:00Z",
    tournament_name: "Tournament",
    state: "CA",
    round_number: 1,
    round_name: null,
    table_number: 1,
    seat_position: 0,
    commander_name: "Commander",
    game_result: "win",
    tournament_player_count: 64,
    ranking_eligible: true,
    opponents: [],
  };
}

describe("fetchRawPlayerLogs", () => {
  beforeEach(() => rpc.mockReset());

  it("paginates bounded RPC responses without truncating lifetime history", async () => {
    rpc
      .mockResolvedValueOnce({
        data: Array.from({ length: 500 }, (_, index) => rpcRow(index)),
        error: null,
      })
      .mockResolvedValueOnce({
        data: Array.from({ length: 500 }, (_, index) => rpcRow(index + 500)),
        error: null,
      })
      .mockResolvedValueOnce({
        data: Array.from({ length: 114 }, (_, index) => rpcRow(index + 1000)),
        error: null,
      });

    const { fetchRawPlayerLogs } = await import(
      "@/app/regional-elo/player/[topdeckId]/player-log-data"
    );
    const rows = await fetchRawPlayerLogs("player-id");

    expect(rows).toHaveLength(1114);
    expect(new Set(rows.map((row) => row.gameId)).size).toBe(1114);
    expect(rpc).toHaveBeenNthCalledWith(1, "get_player_game_logs", {
      p_player_id: "player-id",
      p_limit: 500,
      p_offset: 0,
    });
    expect(rpc).toHaveBeenNthCalledWith(3, "get_player_game_logs", {
      p_player_id: "player-id",
      p_limit: 500,
      p_offset: 1000,
    });
  });
});
