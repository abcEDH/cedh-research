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

import {
  fetchEloDisplayStats,
  overlayEloDisplayStats,
} from "@/lib/elo-display-stats";

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

  it("does not overwrite leaderboard counters when the RPC is unavailable", async () => {
    state.error = { message: "database unavailable" };

    await expect(fetchEloDisplayStats(["player-1"])).resolves.toEqual(
      new Map()
    );
  });

  it("overlays fresh counters onto copied leaderboard rows", async () => {
    state.rows = [
      { topdeck_id: "player-1", games_played: 4, wins: 2, draws: 1, losses: 1 },
    ];
    const rows = [
      { topdeck_id: "player-1", games_played: 20, wins: 10, draws: 5, losses: 5, tier: "A" },
      { topdeck_id: null, games_played: 3, wins: 1, draws: 1, losses: 1, tier: "B" },
    ];

    const overlaid = await overlayEloDisplayStats(rows);

    expect(overlaid).toEqual([
      { ...rows[0], games_played: 4, wins: 2, draws: 1, losses: 1 },
      rows[1],
    ]);
    expect(overlaid[0]).not.toBe(rows[0]);
    expect(overlaid[1]).not.toBe(rows[1]);
  });

  it("preserves persisted counters when the RPC fails", async () => {
    state.error = { message: "database unavailable" };
    const rows = [
      { topdeck_id: "player-1", games_played: 20, wins: 10, draws: 5, losses: 5, tier: "A" },
    ];

    await expect(overlayEloDisplayStats(rows)).resolves.toEqual(rows);
  });
});
