import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  rows: [] as Array<{
    topdeck_id: string;
    games_played: number;
    wins: number;
    draws: number;
    losses: number;
  }>,
  error: null as { message: string } | null,
  rpcCalls: [] as Array<{ name: string; args: unknown }>,
}));

vi.mock("next/cache", () => ({
  unstable_cache: <T extends (...args: unknown[]) => Promise<unknown>>(fn: T) => fn,
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    rpc: vi.fn((name: string, args: unknown) => {
      state.rpcCalls.push({ name, args });
      return Promise.resolve({ data: state.rows, error: state.error });
    }),
  },
}));

import { fetchEloDisplayStats } from "@/lib/elo-display-stats";

describe("fetchEloDisplayStats", () => {
  beforeEach(() => {
    state.rows = [];
    state.rpcCalls = [];
    state.error = null;
  });

  it("uses the bounded aggregate RPC and preserves its W-L-D counters", async () => {
    state.rows = [
      { topdeck_id: "player-1", games_played: 1002, wins: 1, draws: 1, losses: 1000 },
    ];

    const stats = await fetchEloDisplayStats(["player-1"]);

    expect(stats.get("player-1")).toEqual({
      games_played: 1002,
      wins: 1,
      draws: 1,
      losses: 1000,
    });
    expect(state.rpcCalls).toEqual([
      {
        name: "get_elo_display_stats",
        args: { p_topdeck_ids: ["player-1"], p_tier: "ranking" },
      },
    ]);
  });

  it("uses all-game eligibility for the explicit drill-down", async () => {
    state.rows = [
      { topdeck_id: "player-1", games_played: 1, wins: 1, draws: 0, losses: 0 },
    ];

    await fetchEloDisplayStats(["player-1"], "all");

    expect(state.rpcCalls[0]).toEqual({
      name: "get_elo_display_stats",
      args: { p_topdeck_ids: ["player-1"], p_tier: "all" },
    });
  });

  it("falls back to leaderboard counters when the RPC is unavailable", async () => {
    state.error = { message: "database unavailable" };

    await expect(fetchEloDisplayStats(["player-1"])).resolves.toEqual(
      new Map([["player-1", { games_played: 0, wins: 0, draws: 0, losses: 0 }]])
    );
  });
});
