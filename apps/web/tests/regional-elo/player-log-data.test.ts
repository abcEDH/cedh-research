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

  it("fetches one extra row to detect truncated detailed history", async () => {
    rpc.mockResolvedValueOnce({
      data: Array.from({ length: 501 }, (_, index) => rpcRow(index)),
      error: null,
    });

    const { fetchRawPlayerLogPage } = await import(
      "@/app/regional-elo/player/[topdeckId]/player-log-data"
    );
    const page = await fetchRawPlayerLogPage("player-id");

    expect(page.logs).toHaveLength(500);
    expect(page.hasMore).toBe(true);
    expect(rpc).toHaveBeenCalledTimes(1);
    expect(rpc).toHaveBeenNthCalledWith(1, "get_player_game_logs", {
      p_player_id: "player-id",
      p_limit: 501,
      p_offset: 0,
    });
  });
});
